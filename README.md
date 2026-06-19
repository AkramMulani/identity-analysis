# Face Analysis

## Overview
This project is an Identity Analysis system built for the Forensics department. It combines a Flask-based application and a Java Spring Boot service to support face and identity analysis workflows.

## Build and Run

### 1. Run the Flask application
```bash
cd facial_project
pip install -r requirements.txt
flask run
```

### 2. Build and run the Java service
```bash
cd identity-analysis
.\mvnw clean package
java -jar target/*.jar
```

### 3. Open in browser
Use either of these links after the Flask app starts:

- http://localhost:5000
- http://127.0.0.1:5000

## Contact
Genius KODS and Team

contact@geniuskods.com

https://geniuskods.com
