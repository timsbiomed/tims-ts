# Introduction

This repository is a work in progress for running a TIMS terminology server. This is a demo setup for being able to simply clone this repo to your machine and then run:

<<<<<<< HEAD
=======
* `bin/start-ts.sh`  # to start the server
* `bin/stop-ts.sh`  # to stop it.
* `bin/reset-ts.sh`  # to rest to a clean checkout to start over.

>>>>>>> 8d74bd0 (OWL Conversion)
See [this doc](https://docs.google.com/document/d/1J7exF73Z0Z8W-SCYRrQ5qNQVMZTkIH0c4rf-sgjDBfk) for work in progress documentation and notes.

## Prerequisites
1. Java 11+
2. Python 3.8+
3. Docker

## Server management
### Starting the server
1. Run: `bin/start-ts.sh`
2. Open in browser: http://localhost:8080/fhir  
If port `8080` is already being used, look at the logs for some green text in this format, which will show the port chosen `Actions.HapiJpaStarterAction: HAPI FHIR endpoint starting on: http://localhost:PORT/fhir`. Similarly, for PostgreSQL, port `5432` is used by default, but if that is taken, the port chosen can be found in the logs.

## Other workflows
### Converting OWL content
Syntax:
`python bin/convert_owl.py -i INPUT_OWL_PATH -o OUTPUT_DIRECTORY -n OUTPUT_FILENAME`

Example:
`python bin/convert_owl.py -i /Users/joeflack4/projects/owl-on-fhir-content/input/comploinc.owl -o /Users/joeflack4/projects/owl-on-fhir-content/output -n CodeSystem-comploinc.json`
