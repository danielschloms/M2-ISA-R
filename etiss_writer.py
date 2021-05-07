#!/usr/bin/env python3

import argparse
import logging
import pathlib
import pickle
import time

from etiss_architecture_writer import write_arch_struct
from etiss_instruction_writer import write_functions, write_instructions


def setup():
    parser = argparse.ArgumentParser()
    parser.add_argument('top_level')
    parser.add_argument('-s', '--separate', action='store_true')
    parser.add_argument("--log", default="info", choices=["critical", "error", "warning", "info", "debug"])
    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.log.upper()))
    logger = logging.getLogger("etiss_writer")

    top_level = pathlib.Path(args.top_level)
    abs_top_level = top_level.resolve()
    search_path = abs_top_level.parent
    model_path = search_path.joinpath('gen_model')
    spec_name = abs_top_level.stem

    if not model_path.exists():
        raise FileNotFoundError('Models not generated!')

    output_base_path = search_path.joinpath('gen_output')
    output_base_path.mkdir(exist_ok=True)

    logger.info("loading models")
    with open(model_path / (abs_top_level.stem + '_model.pickle'), 'rb') as f:
        models = pickle.load(f)

    start_time = time.strftime("%a, %d %b %Y %H:%M:%S %z", time.localtime())

    return (models, logger, output_base_path, spec_name, start_time, args)

def main():
    models, logger, output_base_path, spec_name, start_time, args = setup()

    for core_name, core in models.items():
        logger.info("processing model %s", core_name)
        output_path = output_base_path / spec_name / core_name
        output_path.mkdir(exist_ok=True, parents=True)

        write_arch_struct(core, start_time, output_path)
        write_functions(core, start_time, output_path)
        write_instructions(core, start_time, output_path, args.separate)

if __name__ == "__main__":
    main()