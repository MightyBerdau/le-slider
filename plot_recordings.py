import argparse
import json
import matplotlib.pyplot as plt

def main(args: argparse.Namespace):
    # Read recording
    with open(args.filepath_recording, 'r') as file:
        rating = json.load(file)

    # Plotting
    fig, ax = plt.subplots()

    ax.plot(rating)
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