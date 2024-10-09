import argparse
import logging
import shutil
import sys
from pathlib import Path
import glob
import subprocess
from motionphoto import create_motion_photo

def validate_directory(dir: Path):
    if not dir.exists():
        logging.error("Path doesn't exist: {}".format(dir))
        exit(1)
    if not dir.is_dir():
        logging.error("Path is not a directory: {}".format(dir))
        exit(1)

def validate_media(photo_path: Path, video_path: Path):
    """
    Checks if the files provided are valid inputs. Supported inputs are MP4/MOV and JPEG filetypes.
    It checks file extensions instead of file signature bytes.
    :param photo_path: path to the photo file
    :param video_path: path to the video file
    :return: True if photo and video files are valid, else False
    """
    if not photo_path.exists():
        logging.error("Photo does not exist: {}".format(photo_path))
        return False
    if not video_path.exists():
        logging.error("Video does not exist: {}".format(video_path))
        return False
    if not photo_path.suffix.lower() in ['.jpg', '.jpeg']:
        logging.error("Photo isn't a JPEG: {}".format(photo_path))
        return False
    if not video_path.suffix.lower() in ['.mov', '.mp4']:
        logging.error("Video isn't a MOV or MP4: {}".format(photo_path))
        return False
    return True

def convert(photo_path: Path, video_path: Path, output_path: Path):
    """
    Merges photo and video, and then adds appropriate metadata for a Google Motion Photo.
    :param photo_path: path to the photo
    :param video_path: path to the video
    :return: None
    """
    create_motion_photo(photo_path, video_path, output_path)

def matching_video(photo_path: Path) -> Path:
    base = str(photo_path.with_suffix(""))
    logging.info("Looking for videos named: {}".format(base))
    files = set(glob.glob(base + ".*"))
    for ext in (".mov", ".mp4", ".MOV", ".MP4"):
        if base + ext in files:
            return Path(base + ext)
    return Path("")

def process_directory(file_dir: Path, recurse: bool):
    """
    Loops through the specified directory and generates a list of (photo, video) path tuples that can be converted.
    :param file_dir: directory to look for photos/videos to convert
    :param recurse: if true, subdirectories will be recursively processed
    :return: a list of tuples containing matched photo/video pairs.
    """
    logging.info("Processing dir: {}".format(file_dir))

    file_pairs = []
    files = file_dir.rglob("*") if recurse else file_dir.iterdir()
    for file in files:
        if file.is_file() and file.suffix.lower() in ['.jpg', '.jpeg'] and matching_video(file) != Path(""):
            file_pairs.append((file, matching_video(file)))

    logging.info("Found {} pairs.".format(len(file_pairs)))
    logging.info("Subset of found image/video pairs: {}".format(str(file_pairs[0:9])))
    return file_pairs

def main(args):
    logging_level = logging.INFO if args.verbose else logging.ERROR
    logging.basicConfig(level=logging_level, stream=sys.stdout)
    logging.info("Enabled verbose logging")

    outdir = args.output if args.output is not None else Path("output")

    if args.dir is not None:
        validate_directory(args.dir)
        pairs = process_directory(args.dir, args.recurse)
        processed_files = set()
        for pair in pairs:
            if validate_media(pair[0], pair[1]):
                convert(pair[0], pair[1], outdir)
                processed_files.add(pair[0])
                processed_files.add(pair[1])

        if args.copyall:
            all_files = set(file for file in args.dir.iterdir() if file.is_file())
            remaining_files = all_files - processed_files

            logging.info("Found {} remaining files to copy.".format(len(remaining_files)))

            if len(remaining_files) > 0:
                outdir.mkdir(parents=True, exist_ok=True)
                for file in remaining_files:
                    file_name = file.name
                    destination_path = outdir / file_name
                    shutil.copy2(file, destination_path)
    else:
        if args.photo is None or args.video is None:
            logging.error("Either --dir or both --photo and --video must be provided.")
            exit(1)

        if validate_media(args.photo, args.video):
            convert(args.photo, args.video, outdir)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Merges a photo and video into a Microvideo-formatted Google Motion Photo')
    parser.add_argument('--verbose', help='Show logging messages.', action='store_true')
    parser.add_argument('--dir', type=Path, help='Process a directory for photos/videos. Takes precedence over '
                                                '--photo/--video')
    parser.add_argument('--recurse', help='Recursively process a directory. Only applies if --dir is provided',
                        action='store_true')
    parser.add_argument('--photo', type=Path, help='Path to the JPEG photo.')
    parser.add_argument('--video', type=Path, help='Path to the MOV/MP4 video.')
    parser.add_argument('--output', type=Path, help='Directory for output files.')
    parser.add_argument('--copyall', help='Copy unpaired files to output directory.', action='store_true')

    main(parser.parse_args())