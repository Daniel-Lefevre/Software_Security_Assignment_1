# **Software Security Assignment 1**

### **Application Purpose**
This project Python-based banking application designed to demonstrate secure software development lifecycle (SSDLC) principles, pipeline security testing (SAST via Jenkins/Bandit), and common web vulnerabilities (such as SQL Injection, Missing Authorization and Improper Input Validation). 

The system is split into three decoupled components communicating over HTTP:
1. **Banking API:** Handles user authentication, token issuance, routing, and input validation/sanitization.
2. **Account Service:** Manages direct secure interactions with the backend SQLite database and enforces resource ownership.
3. **Loan Service:** Evaluates loan requests using an integrated external helper package.

### **Setup Instructions**
This application strictly enforces secure credential management. You must configure the environment variables before running the application.

1. Install the required dependencies & the external dependency:
   `pip install -r requirements.txt`

2. Rename the provided `.env.example` file to `.env` (or create a new `.env` file in the root directory).

3. Populate the `.env` file with a secure string:
   `JWT_SECRET_KEY=your_secure_string_here`

4. Run the application services:
   Because the components are decoupled, you must open **three separate terminal windows** (or tabs), activate your Python environment in each, and start the services concurrently:

   * **Terminal 1 (Banking API):** Run `python banking_api.py` (Listens on port 5000)
   * **Terminal 2 (Account Service):** Run `python account_service.py` (Listens on port 5001)
   * **Terminal 3 (Loan Service):** Run `python loan_service.py` (Listens on port 5002)

6. Test the application:
   Open a final command prompt and run the following command to verify the system is active by reaching the front page of the Banking API:
   `curl -X GET 127.0.0.1:5000`

### **Users in the Database**

| Username | Password   |
|----------|------------|
| Admin    | yT6&vB9!qP |
| John     | Hj4$mX2?kL |
| Mary     | cW8*nR5@zE |
