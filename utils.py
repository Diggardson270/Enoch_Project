import random
import string
import bcrypt
from cryptography.fernet import Fernet
from datetime import datetime
import os
import shutil

def delete_directory(directory_path):
    try:
        shutil.rmtree(directory_path)
        print(f"Directory '{directory_path}' deleted successfully.")
    except OSError as e:
        print(f"Error deleting directory '{directory_path}': {e}")

def check_password(enterd_password:str, hash_password:bytes):
    
    enterd_password_hash = enterd_password.encode("utf-8")
    
    return bcrypt.checkpw(enterd_password_hash, hash_password)
    
    
def generates_hash_password(enterd_password:str):
    
    enterd_password_hash = enterd_password.encode("utf-8")
    salt = bcrypt.gensalt()
    
    password_hash = bcrypt.hashpw(enterd_password_hash, salt)
    
    return password_hash
    
    
    
def generates_random_password():
    
    random_password = random.sample(string.ascii_letters + string.digits, 50)
    random_password = "".join(random_password).encode("utf-8")
    
    salt = bcrypt.gensalt()
    
    random_password_hash = bcrypt.hashpw(random_password, salt)
    
    return random_password_hash
    
    
    


def remove_more_than_one_occurance(item):
    new_list = []
    for x in item:
        if x not in new_list:
            new_list.append(x)
    return new_list

def return_student_and_books(form):
    main_list = []
    for i in form.keys():
        if "_selected" in i:
            book_id = str(i).removesuffix("_selected")
            for students in form.keys():
                if book_id in students:
                    selcted_students = form.get(students).lower().strip().split(",")
            new_list = [book_id, selcted_students]
            main_list.append(new_list)
    return main_list


def encrypt_data(data, key):
    cipher_suite = Fernet(key)
    encrypted_data = cipher_suite.encrypt(data.encode())
    return encrypted_data

def decrypt_data(encrypted_data, key):
    cipher_suite = Fernet(key)
    decrypted_data = cipher_suite.decrypt(encrypted_data).decode()
    return decrypted_data

# def jwt_encrypt():
#     # Generate a key (you should store this key securely)
#     key = generate_key()

#     # Example data
#     data = {"email": "xx@xx.xx", "time_sent": str(datetime.now()), "expire_time": str(datetime.now())}

#     # Convert data to JSON string
#     json_data = str(data)

#     # Encrypt data
#     encrypted_data = encrypt_data(json_data, key)

#     print("Encrypted Data:", encrypted_data)

#     # Decrypt data
#     decrypted_data = decrypt_data(encrypted_data, key)

#     print("Decrypted Data:", decrypted_data)

#     # Check expiration time
#     decrypted_data_dict = eval(decrypted_data)  # Convert string to dictionary
#     expire_time = datetime.strptime(decrypted_data_dict["expire_time"], "%Y-%m-%d %H:%M:%S.%f")
#     current_time = datetime.now()

#     if expire_time < current_time:
#         raise ValueError("Error: Data has expired!")

