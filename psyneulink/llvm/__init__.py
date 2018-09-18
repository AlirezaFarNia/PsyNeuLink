# Princeton University licenses this file to You under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.  You may obtain a copy of the License at:
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
# on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and limitations under the License.


# ********************************************* LLVM bindings **************************************************************

import numpy as np
from llvmlite import binding, ir
import ctypes
import os, sys

from psyneulink.llvm import builtins

__dumpenv = os.environ.get("PNL_LLVM_DUMP")
_module = ir.Module(name="PsyNeuLinkModule")

# TODO: Should this be selectable?
_int32_ty = ir.IntType(32)
_float_ty = ir.DoubleType()
_llvm_generation = 0
_binary_generation = 0


class LLVMBuilderContext:
    def __init__(self):
        self.module = _module
        self.int32_ty = _int32_ty
        self.float_ty = _float_ty

    def get_llvm_function(self, name):
        f = self.module.get_global(name)
        if not isinstance(f, ir.Function):
            raise ValueError("No such function: {}".format(name))
        return f

    def __enter__(self):
        return self

    def __exit__(self, e_type, e_value, e_traceback):
        global _llvm_generation
        _llvm_generation += 1


# Compiler binding
binding.initialize()

# native == currently running CPU
binding.initialize_native_target()

# TODO: This prevents 'LLVM ERROR: Target does not support MC emission!',
# but why?
binding.initialize_native_asmprinter()

__features = binding.get_host_cpu_features().flatten()
__cpu_name = binding.get_host_cpu_name()

# Create compilation target, use default triple
__target = binding.Target.from_default_triple()
__target_machine = __target.create_target_machine(cpu=__cpu_name, features=__features, opt=3)


__pass_manager_builder = binding.PassManagerBuilder()
__pass_manager_builder.inlining_threshold = 99999  # Inline all function calls
__pass_manager_builder.loop_vectorize = True
__pass_manager_builder.slp_vectorize = True
__pass_manager_builder.opt_level = 3  # Most aggressive optimizations

__pass_manager = binding.ModulePassManager()

__target_machine.add_analysis_passes(__pass_manager)
__pass_manager_builder.populate(__pass_manager)

# And an execution engine with an empty backing module
# TODO: why is empty backing mod necessary?
# TODO: It looks like backing_mod is just another compiled module.
#       Can we use it to avoid recompiling builtins?
#       Would cross module calls work? and for GPUs?
__backing_mod = binding.parse_assembly("")

# There are other engines beside MCJIT
# MCJIT makes it easier to run the compiled function right away.
_engine = binding.create_mcjit_compiler(__backing_mod, __target_machine)


__mod = None


def _llvm_build():
    # Remove the old module
    global __mod
    if __mod is not None:
        _engine.remove_module(__mod)
    if __dumpenv is not None and __dumpenv.find("llvm") != -1:
        print(_module)

    # IR module is not the same as binding module.
    # "assembly" in this case is LLVM IR assembly.
    # This is intentional design decision to ease
    # compatibility between LLVM versions.
    __mod = binding.parse_assembly(str(_module))
    __mod.verify()
    __pass_manager.run(__mod)
    if __dumpenv is not None and __dumpenv.find("opt") != -1:
        print(__mod)

    # Now add the module and make sure it is ready for execution
    _engine.add_module(__mod)
    _engine.finalize_object()

    if __dumpenv is not None and __dumpenv.find("compile") != -1:
        global _binary_generation
        print("COMPILING GENERATION: {} -> {}".format(_binary_generation, _llvm_generation))

    # update binary generation
    _binary_generation = _llvm_generation

    # This prints generated x86 assembly
    if __dumpenv is not None and __dumpenv.find("isa") != -1:
        print("ISA assembly:")
        print(__target_machine.emit_assembly(__mod))


_field_count = 0
_struct_count = 0


def _convert_llvm_ir_to_ctype(t):
    if type(t) is ir.VoidType:
        return None
    elif type(t) is ir.PointerType:
        # FIXME: Can this handle void*? Do we care?
        pointee = _convert_llvm_ir_to_ctype(t.pointee)
        return ctypes.POINTER(pointee)
    elif type(t) is ir.IntType:
        # FIXME: We should consider bitwidth here
        return ctypes.c_int
    elif type(t) is ir.DoubleType:
        return ctypes.c_double
    elif type(t) is ir.FloatType:
        return ctypes.c_float
    elif type(t) is ir.LiteralStructType:
        field_list = []
        for e in t.elements:
            # llvmlite modules get _unique string only works for symbol names
            global _field_count
            uniq_name = "field_" + str(_field_count)
            _field_count += 1

            field_list.append((uniq_name, _convert_llvm_ir_to_ctype(e)))

        global _struct_count
        uniq_name = "struct_" + str(_struct_count)
        _struct_count += 1

        def __init__(self, *args, **kwargs):
            ctypes.Structure.__init__(self, *args, **kwargs)

        new_type = type(uniq_name, (ctypes.Structure,), {"__init__": __init__})
        new_type.__name__ = uniq_name
        new_type._fields_ = field_list
        assert len(new_type._fields_) == len(t.elements)
        return new_type
    elif type(t) is ir.ArrayType:
        element_type = _convert_llvm_ir_to_ctype(t.element)
        return element_type * len(t)

    print(t)
    assert(False)


def _convert_python_struct_to_llvm_ir(ctx, t):
    if type(t) is list:
        assert all(type(x) == type(t[0]) for x in t)
        elem_t = _convert_python_struct_to_llvm_ir(ctx, t[0])
        return ir.ArrayType(elem_t, len(t))
    elif type(t) is tuple:
        elems_t = [_convert_python_struct_to_llvm_ir(ctx, x) for x in t]
        return ir.LiteralStructType(elems_t)
    elif isinstance(t, (int, float)):
        return ctx.float_ty
    elif isinstance(t, np.ndarray):
        return _convert_python_struct_to_llvm_ir(ctx, t.tolist())
    elif t is None:
        return ir.LiteralStructType([])

    print(type(t))
    assert(False)

def _convert_ctype_to_python(x):
    if isinstance(x, ctypes.Structure):
        return [_convert_ctype_to_python(getattr(x, field_name)) for field_name, _ in x._fields_]
    if isinstance(x, ctypes.Array):
        return [num for num in x]
    if isinstance(x, ctypes.c_double):
        return x.value
    if isinstance(x, float):
        return x

    print(x)
    assert False


_binaries = {}


class LLVMBinaryFunction:
    def __init__(self, name):
        self.__name = name
        # Binary pointer
        self.ptr = _engine.get_function_address(name)

    def __call__(self, *args, **kwargs):
        return self.c_func(*args, **kwargs)

    # This will be useful for non-native targets
    @property
    def ptr(self):
        return self.__ptr

    @ptr.setter
    def ptr(self, ptr):
        self.__ptr = ptr

        # Recompiled, update the signature
        f = _module.get_global(self.__name)
        assert(isinstance(f, ir.Function))

        return_type = _convert_llvm_ir_to_ctype(f.return_value.type)
        params = []
        self.__byref_arg_types = []
        for a in f.args:
            if type(a.type) is ir.PointerType:
                # remember pointee type for easier initialization
                byref_type = _convert_llvm_ir_to_ctype(a.type.pointee)
                param_type = ctypes.POINTER(byref_type)
            else:
                param_type = _convert_llvm_ir_to_ctype(a.type)
                byref_type = None

            self.__byref_arg_types.append(byref_type)
            params.append(param_type)
        self.__c_func_type = ctypes.CFUNCTYPE(return_type, *params)
        self.__c_func = self.__c_func_type(self.__ptr)

    @property
    def byref_arg_types(self):
        return self.__byref_arg_types

    @property
    def c_func(self):
        return self.__c_func

    @staticmethod
    def get(name):
        if _llvm_generation > _binary_generation:
            _llvm_build()
        if name not in _binaries.keys():
            _binaries[name] = LLVMBinaryFunction(name)
        return _binaries[name]


def _updateNativeBinaries(module, buffer):
    to_delete = []
    # update all pointers that might have been modified
    for k, v in _binaries.items():
        # One reference is held by the _binaries dict, second is held
        # by the k, v tuple here, third by this function, and 4th is the
        # one passed to getrefcount function
        if sys.getrefcount(v) == 4:
            to_delete.append(k)
        else:
            new_ptr = _engine.get_function_address(k)
            v.ptr = new_ptr

    for d in to_delete:
        del _binaries[d]


_engine.set_object_cache(_updateNativeBinaries)

# Initialize builtins
with LLVMBuilderContext() as ctx:
    builtins.setup_vxm(ctx)
