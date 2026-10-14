# **Software Security Assignment 1**

### **Setup Instructions**
This application strictly enforces secure credential management. You must configure the environment variables before running the application.

1. Install the required dependencies & the external dependency:
   `pip install -r requirements.txt`

2. Rename the provided `.env.example` file to `.env` (or create a new `.env` file in the root directory).

3. Populate the `.env` file with a secure string:
   `JWT_SECRET_KEY=your_secure_string_here`

4. Run the application:
   Run `python banking_api.py` and the following command in a command prompt to get to the front page of the banking app `curl -X GET 127.0.0.1:5000`

### **Users in the Database**

| Username | Password   |
|----------|------------|
| Admin    | yT6&vB9!qP |
| John     | Hj4$mX2?kL |
| Mary     | cW8*nR5@zE |
