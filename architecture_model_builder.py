from collections import defaultdict
from functools import partial
from typing import Mapping, Set

from lark import Discard, Transformer

import model_classes


class ArchitectureModelBuilder(Transformer):
    __constants: Mapping[str, model_classes.Constant]
    __address_spaces: Mapping[str, model_classes.AddressSpace]
    __registers: Mapping[str, model_classes.Register]
    __register_file: Mapping[str, model_classes.RegisterFile]
    __register_alias: Mapping[str, model_classes.RegisterAlias]
    __instructions: Mapping[str, model_classes.Instruction]
    __functions: Mapping[str, model_classes.Function]
    __instruction_sets: Mapping[str, model_classes.InstructionSet]
    __read_types: Mapping[str, str]
    __memories: Mapping[str, model_classes.Memory]
    __memory_aliases: Mapping[str, model_classes.Memory]

    def __init__(self):
        self.__constants = {}
        self.__address_spaces = {}
        self.__registers = {}
        self.__register_file = {}
        self.__register_alias = {}
        self.__instructions = {}
        self.__functions = {}
        self.__instruction_sets = {}
        self.__read_types = {}
        self.__memories = {}
        self.__memory_aliases = {}

        self.__scalars = defaultdict(dict)
        self.__fields = defaultdict(partial(defaultdict, list))
        self.__current_instr_idx = 0
        self.__current_fn_idx = 0


    def get_constant_or_val(self, name_or_val):
        if type(name_or_val) == int:
            return name_or_val
        else:
            return self.__constants[name_or_val]

    def Base(self, args):
        return args

    def make_list(self, args):
        return args

    def make_set(self, args):
        return set(args)

    def constants(self, constants):
        return constants

    def address_spaces(self, address_spaces):
        return address_spaces

    def registers(self, registers):
        return registers

    def constant_defs(self, constants):
        return constants

    def functions(self, functions):
        return functions

    def instructions(self, instructions):
        return instructions

    def range_spec(self, args) -> model_classes.RangeSpec:
        return model_classes.RangeSpec(*args)

    def CONST_ATTRIBUTE(self, args) -> model_classes.ConstAttribute:
        return model_classes.ConstAttribute[args.value.upper()]

    def const_attributes(self, args) -> Set[model_classes.ConstAttribute]:
        return set(args)

    def REG_ATTRIBUTE(self, args):
        return model_classes.RegAttribute[args.value.upper()]

    def reg_attributes(self, args):
        return set(args)

    def SPACE_ATTRIBUTE(self, args):
        return model_classes.SpaceAttribute[args.value.upper()]

    def space_attributes(self, args):
        return set(args)

    def INSTR_ATTRIBUTE(self, args):
        return model_classes.InstrAttribute[args.value.upper()]

    def instr_attributes(self, args):
        return set(args)

    def DATA_TYPE(self, args):
        return model_classes.DataType[args.value.upper()]

    def TEXT(self, args):
        return args.value

    def constant_decl(self, args):
        name, default_value = args

        if name in self.__constants:
            raise ValueError(f'Constant {name} already defined!')

        if name in self.__constants: return self.__constants[name]
        c = model_classes.Constant(name, default_value, set())
        self.__constants[name] = c
        return c

    def constant_def(self, args):
        name, value, attributes = args
        if name in self.__constants:
            c = self.__constants[name]
            c.value = value
            c.attributes = attributes
        else:
            c = model_classes.Constant(name, value, attributes)
            self.__constants[name] = c

        return c

    def address_space(self, args):
        name, size, length_base, length_power, attribs = args

        if name in self.__address_spaces:
            raise ValueError(f'Address space {name} already defined!')

        if name in self.__address_spaces: return self.__address_spaces[name]

        size = self.get_constant_or_val(size)
        length_base = self.get_constant_or_val(length_base)
        length_power = self.get_constant_or_val(length_power) if length_power is not None else 1

        a = model_classes.AddressSpace(name, length_base, length_power, size, attribs)
        self.__address_spaces[name] = a

        m = model_classes.Memory(name, model_classes.RangeSpec(length_base, 0, length_power), size, attribs)
        self.__memories[name] = m

        return a

    def register(self, args):
        name, size, attributes = args

        if name in self.__registers:
            raise ValueError(f'Register {name} already defined!')

        if name in self.__registers: return self.__registers[name]

        size = self.get_constant_or_val(size)

        r = model_classes.Register(name, attributes, None, size)
        self.__registers[name] = r

        m = model_classes.Memory(name, model_classes.RangeSpec(0, 0), size, attributes)
        self.__memories[name] = m

        return r

    def register_file(self, args):
        _range, name, size, attributes = args

        if name in self.__register_file:
            raise ValueError(f'Register file {name} already defined!')

        if name in self.__register_file: return self.__register_file[name]

        size = self.get_constant_or_val(size)

        r = model_classes.RegisterFile(name, _range, attributes, size)
        self.__register_file[name] = r

        m = model_classes.Memory(name, _range, size, attributes)
        self.__memories[name] = m

        return r

    def register_alias(self, args):
        name, size, actual, index, attributes = args

        if name in self.__register_alias:
            raise ValueError(f'Register alias {name} already defined!')

        if name in self.__register_alias: return self.__register_alias[name]
        actual_reg = self.__register_file.get(actual) or self.__registers.get(actual) or self.__register_alias.get(actual)
        assert actual_reg
        size = self.get_constant_or_val(size)

        r = model_classes.RegisterAlias(name, actual_reg, index, attributes, None, size)
        self.__register_alias[name] = r

        if not isinstance(index, model_classes.RangeSpec):
            index = model_classes.RangeSpec(index, index)

        parent_mem = self.__memories.get(actual) or self.__memory_aliases.get(actual)
        assert parent_mem
        m = model_classes.Memory(name, index, size, attributes)
        parent_mem.children.append(m)
        self.__memory_aliases[name] = m

        return r

    def bit_field(self, args):
        name, _range, data_type = args
        if not data_type:
            data_type = model_classes.DataType.U

        b = model_classes.BitField(name, _range, data_type)

        self.__fields[self.__current_instr_idx][name].append(b)
        return b

    def BVAL(self, num):
        return model_classes.BitVal(len(num) - 1, int('0'+num, 2))

    def bit_size_spec(self, args):
        size, = args
        return size
    # def scalar_definition(self, args):
    #     name, size = args

    #     assert name not in self.__scalars[self.__current_instr_idx]
    #     if type(size) == int:
    #         s = model_classes.Scalar(name, size=size)
    #     else:
    #         size_const = self.__constants[size]
    #         s = model_classes.Scalar(name, size_const=size_const)

    #     self.__scalars[self.__current_instr_idx][name] = s
    #     return s

    def encoding(self, args):
        return args

    #def operation(self, args):
    #    return args

    # def indexed_reference(self, args):
    #     name, index_expr = args
    #     var = self.__address_spaces.get(name) or self.__register_file.get(name)

    #     assert var
    #     return var, index_expr

    # def named_reference(self, args):
    #     name, = args
    #     var = self.__scalars[self.__current_instr_idx].get(name) or \
    #         self.__fields[self.__current_instr_idx].get(name) or \
    #         self.__constants.get(name) or \
    #         self.__register_alias.get(name) or \
    #         self.__registers.get(name)

    #     assert var
    #     return var

    def instruction(self, args):
        name, attributes, encoding, disass, operation = args

        i = model_classes.Instruction(name, attributes, encoding, disass, operation)

        instr_id = (i.code, i.mask)

        if instr_id in self.__instructions:
            print(f'WARN: overwriting instruction {self.__instructions[instr_id].name} with {name}')

        self.__instructions[instr_id] = i
        self.__current_instr_idx += 1

        return i

    def fn_args_def(self, args):
        return args

    def fn_arg_def(self, args):
        name, data_type, size = args
        if not data_type:
            data_type = model_classes.DataType.U

        size = self.get_constant_or_val(size)

        return model_classes.FnParam(name, size, data_type)

    def function_def(self, args):
        return_len, name, fn_args, data_type, attributes, operation = args

        if not data_type and not return_len:
            data_type = model_classes.DataType.NONE
        elif not data_type:
            data_type = model_classes.DataType.U

        return_len = self.get_constant_or_val(return_len) if return_len else None
        f = model_classes.Function(name, return_len, data_type, fn_args, operation)

        self.__functions[name] = f
        self.__current_fn_idx += 1

        return f

    def instruction_set(self, args):
        name, extension, constants, address_spaces, registers, functions, instructions = args
        constants = {obj.name: obj for obj in constants} if constants else None
        address_spaces = {obj.name: obj for obj in address_spaces} if address_spaces else None
        registers = {obj.name: obj for obj in registers} if registers else None
        #instructions = {obj.name: obj for obj in instructions} if instructions else None

        instructions_dict = None
        if instructions:
            instructions_dict = {}
            for i in instructions:
                instructions_dict[i.name] = i
                i.ext_name = name

        functions_dict = None
        if functions:
            functions_dict = {}
            for f in functions:
                functions_dict[f.name] = f
                f.ext_name = name

        i_s = model_classes.InstructionSet(name, extension, constants, address_spaces, registers, instructions_dict)
        self.__instruction_sets[name] = i_s
        self.__read_types[name] = None

        raise Discard
        return i_s

    def register_default(self, args):
        name, value_or_ref = args

        reg = self.__register_alias.get(name) or self.__registers.get(name)
        assert reg

        val = self.get_constant_or_val(value_or_ref)

        reg._initval = val

        raise Discard

    def core_def(self, args):
        name, _, template, _, _, _, _, _, _ = args
        merged_registers = {**self.__register_file, **self.__registers, **self.__register_alias}
        c = model_classes.CoreDef(name, list(self.__read_types.keys()), template, self.__constants, self.__address_spaces, self.__register_file, self.__registers, self.__register_alias, self.__memories, self.__memory_aliases, self.__functions, self.__instructions)
        return c