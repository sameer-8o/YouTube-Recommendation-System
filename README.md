# YouTube Recommendation Assistant

An interactive Python program for recommending sample videos by category, mood,
or available watch time. Watch Later is stored for the current session only.
The catalogue contains 30 sample videos and does not connect to YouTube.

Python was approved by the lecturer for this project.

## Run

Requires Python 3.7 or later. No external packages are needed.

```sh
python youtube_recommendation_assistant.py
```

## Test

```sh
python -m unittest discover -s tests -v
```

The 21 tests run real command-line sessions. They cover invalid and empty inputs,
Unicode digits, very long numbers, end of input, filtering and sorting, saving
videos, duplicate prevention, duration totals, clearing, and session reset.

## Recent improvements

- Numeric input gives specific feedback and recovers safely from invalid values.
- The Python filename, constants, comments and formatting make the code easier to read.
- Automated tests exercise multiple user scenarios without network access.

These changes are recorded as new commits after the original program import.
View the actual development history with:

```sh
git log --oneline --graph
```
