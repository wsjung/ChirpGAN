# Workflow for scalogram generation

1. Download vocalization files (mp3)

2. Convert mp3 to wave
```
	$ mpg123 -w foo.wav foo.mp3
```

3. Transform
```	
	$ python3 ./makescal file.wav
	> generates .scal file

	$ python3 ./makescal file.scal
	> generates .png scalogram file
```

4. Split wave file into equal-duration files
```
	$ ffmpeg -i FILE.wav -f segment -segment_time [DURATION IN SEC] -c copy [OUTPUT_FILE.wav]

	Ex: $ ffmpeg -i ml-american-robin.wav -f segment -segment_time 1 -c copy robin%01d.wav
	> produces 1 second wave slices of ml-american-robin.wav and saves as robin1.wav ... robinN.wav in cwd
```


# Configurations
- Version 2.24.2020
- voices\_per\_octave = 85
- 3 octaves 
- PNG slices per call (height=256, width=600)

## Notes:
- `scalogram.py` requires scipy.misc.toimage --> `conda install -c conda_forge "scipy<1.2.0"`

## Package installation instructions

```
$ conda create --name <env> --file requirements.txt 
```
