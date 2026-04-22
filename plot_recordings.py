import argparse
import json
import matplotlib.pyplot as plt
import os

from functions.data_io import RatingRecordingSchema

def main(args: argparse.Namespace):
    schema = RatingRecordingSchema.from_json_file(args.filepath_recording)

    # Plotting
    fig, ax = plt.subplots()
    ax.plot(schema.time_stamps, schema.ratings)
    ax.set_xlabel('Time / s')
    ax.set_ylabel('LE / ESCU')
    ax.set_title(f'{os.path.basename(args.filepath_recording)}')
    plt.show()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=('Plots a specified recording.'),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    
    # PATHS (REQUIRED!!!)
    parser.add_argument(
        'filepath_recording',
        help='Name of the file containing recordings to be plotted')
    
    # PLOT ARGS...
    # parser.add_argument(
    #     '--dpi', default = 300, type = int,
    #     help = 'dots per inch')
    
    # parser.add_argument(
    #     '--include_legend', action=argparse.BooleanOptionalAction, default=True,
    #     help = 'some help'

    args = parser.parse_args()

    main(args)