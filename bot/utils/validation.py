import os

def validate_file():
        # file validation, checks video codecs with ffmpeg and converts to mp4 if bitstream is hvec
        os.system("ffprobe -loglevel quiet -select_streams v -show_entries stream=codec_name -of default=nw=1:nk=1 output.mp4 > log.txt 2>&1")
        log_file = open("log.txt","r")
        log_file_content = log_file.read()
        return log_file_content
