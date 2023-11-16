import os
import bcrypt
from flask import Flask, render_template, request, url_for, redirect, send_file, Response, session, flash, get_flashed_messages, jsonify
from flask_sqlalchemy import SQLAlchemy
from typing import List
from sqlalchemy.sql import func
from dataclasses import dataclass
from enum import StrEnum, Enum
import datetime
import qrcode
import secrets
import json
import ast
import math
from statistics import mean
from functools import wraps
import yagmail
from smtplib import SMTPAuthenticationError
from utils import (
    check_password,
    generates_hash_password,
    generates_random_password,
    remove_more_than_one_occurance,
    return_student_and_books,
    encrypt_data,
    decrypt_data, 
    delete_file
)

import dotenv

dotenv.load_dotenv(".env")


sender_email = os.getenv("MY_EMAIL")
sender_password = os.getenv("PASSWORD")
encrypt_key = os.getenv("ENCRYPTION_KEY")


app = Flask(__name__)
app.secret_key = "8419c249452b7241d1f7f3da3e4f9df359af0a264a988d999d408406f0976788"


basedir = os.path.abspath(os.path.dirname(__file__))

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + \
    os.path.join(basedir, 'db.sqlite3')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True


db = SQLAlchemy(app)


def login_required(func):
    @wraps(func)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for('login'))
        return func(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" in session:
            if session["user"]["user_type"] == UserType.ADMIN:
                return f(*args, **kwargs)
            else:
                return redirect("/")
    return decorated_function


class UserType(StrEnum):
    ADMIN = "admin"
    LIBERIAN = "liberian"
    STUDENT = "student"


class StudentLevel(Enum):
    LEVEL_100 = "100"
    LEVEL_200 = "200"
    LEVEL_300 = "300"
    LEVEL_400 = "400"
    LEVEL_500 = "500"


@dataclass
class LoggedIn:
    firstname: str = None
    lastname: str = None
    password: str = None
    email: str = None
    user_type: str = None


class User(db.Model):

    # __tablename__ = "user"
    __table_args__ = (db.UniqueConstraint('email'), )

    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(100), nullable=False)
    lastname = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String, nullable=False)
    email = db.Column(db.String(80), unique=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now())
    user_type = db.Column(db.String(10), db.DefaultClause(UserType.ADMIN))
    is_verified = db.Column(db.Boolean, default=False,
                            server_default="False", nullable=False)

    # def __repr__(self):
    #     return f'<Student {self.firstname}>'

    # def __str__(self) -> str:
    #     return f'User {self.email}'



class Department(db.Model):
    __table_args__ = (db.UniqueConstraint('name'), )
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    students: db.Mapped[List["Student"]] = db.relationship(
        'Student', back_populates="department", cascade="all, delete-orphan")

    def __str__(self) -> str:
        return f'User {self.name}'

    @property
    def number_of_students(self):
        return len(self.students)


class Student(db.Model):

    # __tablename__ = "students"
    __table_args__ = (db.UniqueConstraint('matirc_number', 'user_id'), )

    id = db.Column(db.Integer, primary_key=True)
    user = db.relationship(User, lazy=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    matirc_number = db.Column(
        db.String(11), server_default="False", nullable=False)
    student_level = db.Column(db.Integer, nullable=False)
    books_borrowed: db.Mapped[List['BorowedBook']] = db.relationship(
        'BorowedBook', back_populates="student", cascade="all, delete-orphan")
    bio = db.Column(db.Text)
    department = db.relationship(Department, lazy=True)
    department_id = db.Column(
        db.Integer, db.ForeignKey(Department.id), nullable=False)

    def __repr__(self):
        return f'<Student {self.id}>'

    def __str__(self) -> str:
        return f'User {self.id}'

    def borrowed(self):
        returned = list()
        not_returned = list()
        for book in self.books_borrowed:
            if bool(book.is_returened):
                returned.append(book)
            else:
                not_returned.append(book)
        return returned, not_returned

    @property
    def number_of_returned_books(self):
        return len(self.borrowed()[0])

    @property
    def number_of_not_returned_books(self):
        return len(self.borrowed()[1])

    @property
    def total_books_borrowed(self):
        return self.number_of_not_returned_books + self.number_of_returned_books
    
    
    
    @property
    def qr_dir(self):
        fullname = f"{self.user.firstname} {self.user.lastname}".title().strip()
        qr_dir = f'students/{fullname.lower().replace(" ", "-")}.png'
        return qr_dir


class Author(db.Model):

    # __tablename__ = "authors"

    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(100), nullable=False)
    lastname = db.Column(db.String(100), nullable=False)
    books: db.Mapped[List["Book"]] = db.relationship(
        'Book', back_populates="author", cascade="all, delete-orphan")

    def __str__(self) -> str:
        return f'User {self.id}'

    @property
    def no_of_books(self):
        return len(self.books)


class Category(db.Model):
    __table_args__ = (db.UniqueConstraint('name'), )
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    books: db.Mapped[List["Book"]] = db.relationship(
        'Book', back_populates="category", cascade="all, delete-orphan")

    def __str__(self) -> str:
        return f'User {self.name}'

    @property
    def no_of_books(self):
        return len(self.books)


class Book(db.Model):

    # __tablename__ = "books"

    __table_args__ = (db.UniqueConstraint('title'), )

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    author = db.relationship(Author, lazy=True)
    author_id = db.Column(db.Integer, db.ForeignKey(Author.id), nullable=False)
    category = db.relationship(Category, lazy=True)
    category_id = db.Column(
        db.Integer, db.ForeignKey(Category.id), nullable=False)
    no_of_stock = db.Column(db.Integer, server_default='0', nullable=False)
    # no_borrowed = db.Column(db.Integer, server_default='0', nullable=False)
    date_added = db.Column(db.DateTime(timezone=True),
                           server_default=func.now())
    slug = db.Column(db.String, nullable=False)

    def __repr__(self):
        return f'<Book {self.title}>'

    def __str__(self) -> str:
        return f'User {self.id}'

    @property
    def no_of_borrowd_days(self):
        if self.no_of_stock < 10:
            return 6
        else:
            return 10

    @property
    def slug(self) -> str:
        if self.title is not None:
            return self.title.strip().replace(" ", "-").lower()
        return "None"

    @property
    def no_borrowed(self):
        borrowed_books = BorowedBook.query.filter_by(
            book_id=self.id, is_returened=False).all()
        # return len(borrowed_books)
        return len(borrowed_books)
    
    
    @property
    def  qr_dir(self):
        qr_dir = f"book_qrcodes/{self.slug}.png"
        return qr_dir


class BorowedBook(db.Model):

    # __tablename__ = "borrored-books"

    id = db.Column(db.Integer, primary_key=True)
    book = db.relationship(Book, lazy=True)
    book_id = db.Column(db.Integer, db.ForeignKey(Book.id), nullable=False)
    student_id = db.Column(
        db.Integer, db.ForeignKey(Student.id), nullable=False)
    student = db.relationship(Student, lazy=True)
    is_returened = db.Column(db.Boolean, default=False,
                             server_default="False", nullable=False)
    return_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    borrowed_date = db.Column(db.DateTime(timezone=True),
                              server_default=func.now())

    def __str__(self) -> str:
        return f"Hello {self.id}"

    @property
    def remaining_days(self):
        days_left = self.return_date - self.borrowed_date
        if days_left.days < 0:
            return "0:00:00"
        elif self.is_returened:
            return None
        return f"{days_left.days} days"

    @property
    def return_date_cleaned(self):
        return f"{self.return_date.year}-{self.return_date.month}-{self.return_date.day} {self.return_date.hour}:{self.return_date.minute}"


@app.route("/", methods=["GET", "POST"])
@login_required
def home(*args, **kwargs):
    # Retrieve all books
    books = Book.query.all()

    # Retrieve all borrowed books that haven't been returned
    borrowed = BorowedBook.query.filter_by(is_returened=False).all()

    # Retrieve all categories
    categories = Category.query.all()

    # Calculate the total number of books in stock
    no_of_books = sum([i.no_of_stock for i in books])

    # Calculate the total number of books borrowed
    no_borrowed = len(BorowedBook.query.filter_by(is_returened=False).all())

    # Reverse the list of borrowed books
    borrowed.reverse()

    # Retrieve the 6 most recently borrowed books
    recently_borrowed_books = borrowed[:6]

    # Initialize variables
    average_borrowed = 0
    most_borrowes = 0
    others = 0
    percentage = 0
    total_borrowes = 0

    # Calculate the average number of times a book has been borrowed
    if len(books) > 0:
        average_borrowed = round(mean([i.no_borrowed for i in books]))

        # Retrieve the books that have been borrowed more than the average
        most_borrowes = [i for i in books if i.no_borrowed > average_borrowed]

        # Calculate the total number of times books have been borrowed less than the average
        others = sum([i.no_borrowed for i in books if i.no_borrowed < average_borrowed])

        # Calculate the percentage of borrowed books out of the total number of books
        percentage = round((no_borrowed/no_of_books)*100)

        # Calculate the total number of times books have been borrowed, excluding the ones borrowed less than the average
        total_borrowes = others + sum([i.no_borrowed for i in most_borrowes])

    # Create a context dictionary to pass to the template
    context = {
        "recently_borrowed_books": recently_borrowed_books,
        "categories": categories,
        "len_categories": len(categories),
        "books": books[:6],
        "no_of_books": no_of_books,
        "no_borrowed": no_borrowed,
        "percentage": percentage,
        "most_borrowed": most_borrowes,
        "others": others,
        "total_borrowes": total_borrowes
    }

    # Render the index.html template with the context variables
    return render_template("index.html", context=context)


@app.route("/books/", methods=["GET", "POST"])
@login_required
def get_and_create_books():
    # Get all authors, books, and categories from the database
    authors = Author.query.all()
    books = Book.query.all()
    categories = Category.query.all()

    if request.method == "POST":
        # Retrieve book details from the request form
        title = request.form["book_title"]
        author = request.form["book_author"]
        category_id = request.form["book_category"]
        stock = request.form["no_in_stock"]

        # Create a new book object
        book = Book()
        book.author_id = author
        book.title = title.lower().strip()
        book.category_id = category_id
        book.no_of_stock = stock

        # Check if a book with the same title already exists
        existing_book_title = Book.query.filter_by(title=book.title).first()

        if existing_book_title:
            # Display an error message if the book title already exists
            flash("Sorry, but this title already exists!!! ")
        else:
            # Save the new book to the database
            db.session.add(book)
            db.session.commit()

            # Create a dictionary with book details for generating a QR code
            data = {
                "title": book.title,
                "author_id": book.author_id,
                "author_firstname": book.author.firstname,
                "author_lastname": book.author.lastname,
                "category_id": book.category_id,
                "category_name": book.category.name
            }

            # Generate a QR code for the book and save it to the static directory
            book_qrcode = qrcode.make(data=data, box_size=4, border=5)
            book_qrcode.save(f"static/{book.qr_dir}")

            # Redirect to the books page after successfully creating a book
            return redirect("/books/")

    # Prepare the context with authors, books, and categories for rendering the template
    context = {
        "authors": authors,
        "books": books,
        "categories": categories
    }

    # Render the template with the context
    return render_template("books.html", context=context)


@app.route("/book/<int:id>/", methods=["GET", "POST"])
@login_required
def book_detail_page(id, *args, **kwargs):
    """
    View function for the book detail page.
    """
    # Get the book details
    book = Book.query.get_or_404(id)
    authors = Author.query.all()
    categories = Category.query.all()

    # Get the list of borrowed books for the current book
    borrowed_books = BorowedBook.query.filter_by(book_id=id).all()

    if request.method == "POST":
        # Check if the book title already exists
        existing_book_title = Book.query.filter_by(
            title=request.form["title"]).first()
        if existing_book_title:
            flash("Sorry, but this title already exists!!! ")
        else:
            # Update the book details
            for key in request.form:
                if request.form[key] != "":
                    if hasattr(book, key):
                        try:
                            setattr(book, str(key), request.form[key])
                        except AttributeError:
                            pass
            # Generate and save the QR code for the book
            data = {
                "title": book.title,
                "author_id": book.author_id,
                "author_firstname": book.author.firstname,
                "author_lastname": book.author.lastname,
                "category_id": book.category_id,
                "category_name": book.category.name
            }
            book_qrcode = qrcode.make(data=data, box_size=4, border=5)
            book_qrcode.save(f"static/{book.qr_dir}")
            db.session.commit()
            return redirect(url_for("book_detail_page", id=id))

    # Delete the book and its borrowed books if requested
    if request.args.get("delete") == "true":
        borrowed_books = BorowedBook.query.filter_by(book_id=book.id)
        for borroewd in borrowed_books:
            db.session.delete(borroewd)
        delete_file(f"static/{book.qr_dir}")
        db.session.delete(book)
        db.session.commit()
        return redirect(url_for("get_and_create_books"))

    # Update the status of a borrowed book if returned or not returned
    if request.args.get("returned"):
        borrowed_book = BorowedBook.query.get_or_404(request.args.get("id"))
        if borrowed_book:
            borrowed_book.is_returened = request.args.get("returned") == "true"
            if borrowed_book.is_returened:
                book.no_of_stock += 1
            else:
                book.no_of_stock -= 1
            db.session.commit()
            return redirect(url_for("book_detail_page", id=id))

    # Prepare the context for rendering the template
    context = {
        "book": book,
        "authors": authors,
        "categories": categories,
        "borrowed_books": borrowed_books,
        "qr_code": url_for('static', filename=f"{book.qr_dir}"),
    }
    return render_template("bookdetails.html", context=context)


@app.route("/students/", methods=["GET", "POST"])
@login_required
def get_and_create_student():
    # Get all students from the database
    students = Student.query.all()
    departments = Department.query.all()

    if request.method == "POST":
        # Get the form data
        first_name = request.form["first_name"]
        last_name = request.form["last_name"].lower().strip()
        email = request.form["email"]
        level = request.form["student_level"]
        matric_number = request.form["matric_number"].lower().strip()
        department = request.form["department"]

        # Create a new user
        user = User()
        user.firstname = first_name.lower().strip()
        user.lastname = last_name.lower().strip()
        user.email = email
        user.password = "nill"
        user.user_type = UserType.STUDENT

        # Check if user with the same email or matric number already exists
        existing_user_email = user.query.filter_by(email=user.email).first()
        existing_user_matric_number = Student.query.filter_by(
            matirc_number=matric_number).first()

        # If user already exists, show error messages
        if existing_user_email or existing_user_matric_number:
            if existing_user_email:
                flash("Sorry, but this email already exits!!! ")
            if existing_user_matric_number:
                flash("Sorry, but this matric number already exits!!! ")
        else:

            # Add the new user to the database
            db.session.add(user)
            db.session.flush()

            # Create a new student
            student = Student()
            student.user_id = user.id
            student.student_level = level
            student.matirc_number = matric_number
            student.department_id = department
            db.session.add(student)
            db.session.flush()
            fullname = f"{student.user.firstname} {student.user.lastname}".title().strip()
            # Generate the QR code and save it
            data = {
                "user id": user.id,
                "name": fullname,
                "email": user.email,
                "level": student.student_level,
                "department": student.department.name
            }
            student_qrcode = qrcode.make(data=data, box_size=4, border=5)
            student_qrcode.save(f"static/{student.qr_dir}")

            # Add the new student to the database
            db.session.add(student)
            db.session.commit()

            # Redirect to the students page
            return redirect("/students/")

    # Prepare the context for rendering the template
    context = {
        "students": students,
        "levels": StudentLevel,
        "departments":departments
    }

    # Render the students page
    return render_template("students.html", context=context)


@app.route("/student/<int:id>/", methods=["GET", "POST"])
@login_required
def student_detail_page(id, *args):
    """
    View function for displaying and updating student details.
    """

    # Get the student and user and department from the database
    student = Student.query.get_or_404(id)
    user = User.query.get_or_404(student.user_id)
    departments = Department.query.all()

    # Generate full name and QR code file name
    fullname = f"{student.user.firstname} {student.user.lastname}".title().strip()

    # Generate previous full name and QR code file directory
    previous_first_name = user.firstname
    previous_last_name = user.lastname
    previous_fullname = f"{previous_first_name} {previous_last_name}".title().strip()
    previous_qr_dir = f'static/students/{previous_fullname.lower().replace(" ", "-")}.png'

    # Get all borrowed books for the student
    borrowed_books = BorowedBook.query.filter_by(student_id=id).all()

    if request.method == "POST":
        for key in request.form:
            if request.form[key] != "":
                # Check if the email and matric number already exist
                existing_user_email = user.query.filter_by(email=request.form["email"]).first()
                existing_user_matric_number = Student.query.filter_by(matirc_number=request.form["matirc_number"]).first()

                if existing_user_email:
                    flash("Sorry, but this email already exits!!! ")
                if existing_user_matric_number:
                    flash("Sorry, but this matric number already exits!!! ")
                else:
                    # Update student and user attributes
                    if hasattr(student, key):
                        try:
                            setattr(student, str(key), request.form[key])
                        except AttributeError:
                            pass
                    if hasattr(user, key):
                        try:
                            setattr(user, str(key), request.form[key])
                        except AttributeError:
                            pass

                    # Remove previous QR code file
                    os.remove(os.path.join(basedir, previous_qr_dir))

             

                    # Generate data for QR code
                    data = {
                        "user id": user.id,
                        "name": fullname,
                        "email": user.email,
                        "level": student.student_level,
                        "matric_number": student.matirc_number
                    }

                    # Generate and save student QR code
                    student_qrcode = qrcode.make(data=data, box_size=4, border=5)
                    student_qrcode.save(f"static/{student.qr_dir}")

                    # Commit changes to the database and redirect to the updated student detail page
                    db.session.commit()
                    return redirect(url_for("student_detail_page", id=id))

    if request.args.get("delete") == "true":
        # Delete borrowed books and student/user records from the database
        borrowed_books = BorowedBook.query.filter_by(student_id=student.id)
        for borroewd in borrowed_books:
            db.session.delete(borroewd)
        delete_file(f"static/{student.qr_dir}")
        db.session.delete(student)
        db.session.delete(user)
        db.session.commit()
        return redirect(url_for("get_and_create_student"))

    context = {
        "student": student,
        "qr_code": url_for('static', filename=f"{student.qr_dir}"),
        "levels": StudentLevel,
        "departments":departments
    }
    return render_template("studentdetails.html", context=context)


@app.route('/qrcode/<path:filename>/')
def download_file(filename: str):
    return send_file(filename, as_attachment=True)


@app.route("/borrow_book/", methods=["GET", "POST"])
@login_required
def borrow_book(*args, **kwargs):
    selection = []
    students = Student.query.all()
    books = Book.query.all()
    categories = Category.query.all()
    selected_students = []
    selected_books = []
    not_found = []
    not_enough_in_stock = []
    students_matirc_number_list = [student.matirc_number for student in students]  
    if request.args:
        if request.args.get("submit_method")== "use_qr_code":
            return redirect(url_for("borrow_with_qr"))
        else:
            if request.args.get("submit_method")== "input_manually":
            
                if request.method =="POST": 
                    selection = return_student_and_books(request.form)
                    session_selection = []
                    for i in selection:
                        session_selection.append([i[0], str(i[1])])
                    session["selection"] = session_selection
                    for _book_id, _students in selection:
                        selected_books.extend([book for book in books if book.id == int(_book_id)])
                        for matric_number in _students:
                            matric_number = matric_number.lower().strip()
                            print(matric_number)
                            if matric_number in students_matirc_number_list:
                                student = Student.query.filter_by(matirc_number=matric_number).first()
                                selected_students.append(student)
                            # else:
                            #     not_found.append(matric_number)  
                    not_found = remove_more_than_one_occurance(not_found)  
                    selected_students = remove_more_than_one_occurance(selected_students)   
                    number_of_books = len(selected_books)   
                          
                    borrow_form_context = {
                        "books":selected_books,
                        "students":selected_students,
                        "number_of_books":number_of_books,
                        "not_found": not_found,
                        "not_enough_in_stock":not_enough_in_stock
                    }
                    return render_template("borrow_form.html", context=borrow_form_context)  
                book_page_context = {
                            "books":books,
                            "categories":categories
                }  
                return render_template("select_book.html", context=book_page_context) 
            elif request.args.get("continue") == "True":
                for book_id, students_selected in session["selection"]:
                    students = remove_more_than_one_occurance([i.lower().strip() for i in ast.literal_eval(students_selected)])
                    print(students)
                    for matirc_number in students:
                        borrowed_book = BorowedBook()
                        student = Student.query.filter_by(matirc_number=matirc_number).first()
                        book = Book.query.get_or_404(book_id)
                        borrowed_book.book_id = book.id
                        if student != None:
                            borrowed_book.student_id = student.id
                            borrowed_book.return_date = datetime.timedelta(days=book.no_of_borrowd_days) + datetime.datetime.now()
                            book.no_of_stock -= 1
                            db.session.add(borrowed_book)
                            db.session.commit()
                return redirect(url_for("get_and_create_books"))
    return render_template("select_method.html") 





@app.route("/borrow/borrow_with_qr/", methods=["GET", "POST"])
def borrow_with_qr(*args, **kwargs):
    """
    Endpoint for borrowing a book using a QR code.
    Accepts user_id and book_title as query parameters.
    """
    if request.args.get("user_id") and request.args.get("book_title"):
        session.pop("user_id", None)
        # Find the student with the given user_id
        student = Student.query.filter_by(user_id=request.args.get("user_id")).first()
        # Find the book with the given title
        book = Book.query.filter_by(title=request.args.get("book_title")).first()

        if student is not None and book is not None:
            if request.method == "POST":
                # Create a new instance of BorrowedBook
                borrow_book = BorowedBook(book_id=book.id, student_id=student.id)
                db.session.add(borrow_book)
                db.session.commit()
                return redirect(url_for("home"))
            context = {
                "student": student,
                "book": book,
                "no_of_pending_books": len([book for book in student.books_borrowed if book.is_returned == False])
            }
            return render_template("book_qrcode_submit.html", context=context)

    elif request.args.get("user_id") is not None:
        # Find the student with the given user_id
        student = Student.query.filter_by(user_id=request.args.get("user_id")).first()
        if student is not None:
            session["user_id"] = student.user_id
            if request.method == "POST":
                return redirect(url_for("scan"))
            context = {
                "student": student,
                "no_of_pending_books": len([book for book in student.books_borrowed if book.is_returned == False])
            }
            return render_template("user_qrcode_submit.html", context=context)

    return redirect(url_for("scan"))


@app.route("/categories/", methods=["GET", "POST"])
@login_required
def get_and_create_category():
    # Get all categories from the database
    categories = Category.query.all()

    # If the request method is POST, create a new category
    if request.method == "POST":
        # Get the name of the category from the form data
        name = request.form["name"].lower().strip()

        # Create a new Category object
        category = Category()
        category.name = name

        # Check if a category with the same name already exists
        existing_category_name = category.query.filter_by(
            name=category.name).first()

        # If the category already exists, display an error message
        if existing_category_name:
            flash("Sorry, but this category already exists!!! ")
        # Otherwise, add the category to the database and redirect to the categories page
        else:
            db.session.add(category)
            db.session.commit()
            return redirect("/categories/")

    # Prepare the context for rendering the template
    context = {
        "categories": categories,
    }

    # Render the categories.html template with the provided context
    return render_template("categories.html", context=context)


@app.route("/category/<int:id>/", methods=["GET", "POST"])
@login_required
def category_detail_page(id, *args, **kwargs):
    """
    Render the category detail page and handle form submission.

    Args:
        id (int): The id of the category.

    Returns:
        str: The rendered template.
    """

    category = Category.query.get_or_404(id)

    if request.method == "POST":
        for key in request.form:
            if request.form[key] != "":
                existing_category = Category.query.filter_by(
                    name=request.form["name"]).first()
                if existing_category:
                    flash("Sorry, but this category name already exists!")
                else:
                    category.name = request.form["name"]
                    db.session.commit()
                    return redirect(url_for("category_detail_page", id=id))

    if request.args.get("delete") == "true":
        db.session.delete(category)
        db.session.commit()
        return redirect(url_for("get_and_create_category"))

    context = {
        "category": category,
    }
    return render_template("categorydetails.html", context=context)




@app.route("/departments/", methods=["GET", "POST"])
@login_required
def get_and_create_department():
    # Get all department from the database
    department = Department.query.all()

    # If the request method is POST, create a new department
    if request.method == "POST":
        # Get the name of the category from the form data
        name = request.form["name"].lower().strip()

        # Create a new Department object
        department = Department()
        department.name = name

        # Check if a department with the same name already exists
        existing_category_name = department.query.filter_by(
            name=department.name).first()

        # If the department already exists, display an error message
        if existing_category_name:
            flash("Sorry, but this department already exists!!! ")
        # Otherwise, add the department to the database and redirect to the departments page
        else:
            db.session.add(department)
            db.session.commit()
            return redirect("/departments/")

    # Prepare the context for rendering the template
    context = {
        "departments": department,
    }

    # Render the departments.html template with the provided context
    return render_template("departments.html", context=context)


@app.route("/department/<int:id>/", methods=["GET", "POST"])
@login_required
def department_detail_page(id, *args, **kwargs):
    """
    Render the department detail page and handle form submission.

    Args:
        id (int): The id of the category.

    Returns:
        str: The rendered template.
    """

    department = Department.query.get_or_404(id)

    if request.method == "POST":
        for key in request.form:
            if request.form[key] != "":
                existing_department = Department.query.filter_by(
                    name=request.form["name"]).first()
                if existing_department:
                    flash("Sorry, but this category name already exists!")
                else:
                    department.name = request.form["name"]
                    db.session.commit()
                    return redirect(url_for("department_detail_page", id=id))

    if request.args.get("delete") == "true":
        students = Student.query.filter_by(department=department).all()
        db.session.delete(department)
        for student in students:
            db.session.delete(student)
        db.session.commit()
        return redirect(url_for("get_and_create_department"))

    context = {
        "department": department,
    }
    return render_template("departmentsdetails.html", context=context)


@app.route("/authors/", methods=["GET", "POST"])
@login_required
def get_and_create_author():
    # Retrieve all authors from the database
    authors = Author.query.all()

    if request.method == "POST":
        # Extract first name and last name from the form data
        first_name = request.form["firstname"].lower().strip()
        last_name = request.form["lastname"].lower().strip()

        # Create a new Author instance
        author = Author()
        author.firstname = first_name
        author.lastname = last_name

        # Check if an author with the same first name and last name already exists
        existing_author = author.query.filter_by(
            firstname=first_name, lastname=last_name).first()

        if existing_author:
            flash("Sorry, but this author already exists!")
        else:
            # Add the new author to the database and commit the changes
            db.session.add(author)
            db.session.commit()
            return redirect("/authors/")

    # Prepare the context for rendering the template
    context = {
        "authors": authors,
    }

    # Render the authors.html template with the provided context
    return render_template("authors.html", context=context)


@app.route("/author/<int:id>/", methods=["GET", "POST"])
@login_required
def author_detail_page(id, *args):
    """
    Handle GET and POST requests for author detail page.
    
    Args:
        id (int): The ID of the author.
        *args: Additional arguments.
        
    Returns:
        The rendered template for the author detail page.
    """
    author = Author.query.get_or_404(id)

    if request.method == "POST":
        # Update the author attributes with form data
        for key in request.form:
            if request.form[key] != "":
                if hasattr(author, key):
                    try:
                        setattr(author, str(key), request.form[key])
                    except AttributeError:
                        pass
                db.session.commit()
                return redirect(url_for("author_detail_page", id=id))

    if request.args.get("delete") == "true":
        # Delete the author from the database
        db.session.delete(author)
        db.session.commit()
        return redirect(url_for("get_and_create_author"))
    
    # Prepare the context for rendering the template
    context = {
        "author": author,
    }
    return render_template("authordetails.html", context=context)


@app.route("/user/", methods=["GET", "POST"])
def detail_page(*args):
    """
    This function handles the GET and POST requests for the '/user/' route.
    It renders the 'user.html' template and returns it as the response.
    """
    return render_template("user.html")


@app.route("/user/settings/", methods=["GET", "POST"])
def user_settings_page(*args, **kwargs):
    # Initialize an empty dictionary to store input data
    inputs_data = {}

    # Create a copy of the user session
    new_session = session["user"].copy()

    # Retrieve the user from the database based on the email in the session
    user = User.query.filter_by(email=session["user"]["email"]).first()

    if request.method == "POST":
        # Check if any of the form fields have been filled
        if (
            request.form.get("firstname") != ""
            or request.form.get("lastname") != ""
            or request.form.get("emailaddress") != ""
            or request.form.get("newpassword") != ""
        ):
            # Update the user's first name if provided
            if request.form.get("firstname"):
                firstname = request.form.get("firstname")
                inputs_data["firstname"] = firstname

            # Update the user's last name if provided
            if request.form.get("lastname"):
                lastname = request.form.get("lastname")
                inputs_data["lastname"] = lastname

            # Update the user's email address if provided
            if request.form.get("emailaddress"):
                email = request.form.get("emailaddress")
                password = request.form.get("confirmemailpassword")
                if not check_password(password, user.password):
                    flash("Invalid Password")
                inputs_data["email"] = email

            # Update the user's password if provided
            if request.form.get("newpassword"):
                newpassword = request.form.get("newpassword")
                confirmpassword = request.form.get("confirmpassword")
                currentpassword = request.form.get("currentpassword")

                if newpassword != confirmpassword:
                    flash("Invalid Password")

                if not check_password(currentpassword, user.password):
                    flash("Invalid Password")
                inputs_data["password"] = generates_hash_password(newpassword)

            # Update the user object with the input data
            for key in inputs_data:
                if hasattr(user, key):
                    setattr(user, key, inputs_data[key])

            # Commit the changes to the database
            db.session.commit()

            # Update the session with the new input data
            for key in new_session:
                if key in inputs_data:
                    new_session[key] = inputs_data[key]

            session["user"] = new_session

        # Redirect to the user settings page
        return redirect(url_for("user_settings_page"))

    # Render the user settings page
    return render_template("user_settings.html")

@app.route("/login/", methods=["GET", "POST"])
def login(*args, **kwargs):
    """
    Handle the login functionality.

    This function handles both the GET and POST requests to the "/login/" route.
    For a POST request, it checks the email and password provided in the form,
    verifies the user's credentials, and sets the user session if successful.
    For a GET request, it renders the login template.

    Returns:
        If the user is successfully logged in, it redirects to the home route.
        Otherwise, it renders the login template.
    """
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = User.query.filter_by(email=email).first()
        if user is not None:
            if check_password(password, user.password):
                if user.is_verified:
                    logged = LoggedIn(
                        **{field: vars(user).get(field)
                           for field in vars(user) if field in vars(LoggedIn)})
                    session["user"] = vars(logged)
                    return redirect(url_for("home"))
                else:
                    flash("Please verify your email", category="warning")
            else:
                flash("Invalid email or password", category="warning")
        else:
            flash("This account does not exist", category="warning")
    return render_template("login.html")



@app.route("/logout/")
@login_required
def logout(*args, **kwargs):
    """
    Log out the user by removing the user session and redirecting to the login page.

    Args:
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.

    Returns:
        Response: Redirects to the login page.
    """
    session.pop("user", None)
    return redirect(url_for("login"))



@app.route("/json_categories/", methods=["GET"])
def request_categories():
    """
    This function handles the GET request for retrieving JSON categories.
    It fetches all categories from the Category table and returns a JSON response.

    Returns:
        A JSON response containing the categories and the number of books in each category.
    """
    data = []
    categories = Category.query.all()

    for category in categories:
        new_data = {
            "name": category.name,
            "no_of_books": len(category.books)
        }
        data.append(new_data)

    return jsonify(data)


@app.route("/scan/", methods=["GET", "POST"])
def scan(*args, **kwargs):
    """
    Route handler for the "/scan/" endpoint.

    This function renders the "scan.html" template.

    Args:
        *args: Variable-length argument list.
        **kwargs: Variable-length keyword argument list.

    Returns:
        Response: Rendered HTML template for the "scan.html" page.
    """
    
    # Render the HTML template for the "scan.html" page
    return render_template("scan.html")



@app.route("/clean_data/", methods=["GET", "POST"])
def clean_and_return_id(*args, **kwargs):
    """
    Clean the data and redirect to the appropriate URL based on the data.

    Args:
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.

    Returns:
        Response: Flask response object.

    Raises:
        None
    """
    # Get the data from the request arguments
    data = request.args.get("data").strip()

    # Convert the data to a dictionary
    result = ast.literal_eval(data)

    if "title" in result:
        # If 'title' key exists in the result, redirect to borrow_with_qr with user_id and book_title parameters
        return redirect(f"/borrow/borrow_with_qr/?user_id={session['user_id']}&book_title={result['title']}")
    else:
        # Redirect to borrow_with_qr with user_id parameter
        return redirect(f"/borrow/borrow_with_qr/?user_id={result['user id']}")


@app.route("/librarians/", methods=["GET", "POST"])
@login_required
@admin_required
def get_and_create_liberian():
    """
    This function handles the GET and POST requests for the '/librarians/' route.
    If the request method is POST, it creates a new librarian user and sends a password reset email.
    If the request method is GET, it retrieves all the librarian users and renders the 'librarians.html' template.
    """
    # Retrieve all librarian users
    librarians = User.query.filter_by(user_type=UserType.LIBERIAN).all()

    if request.method == "POST":
        # Get form data
        first_name = request.form["firstname"].lower().strip()
        last_name = request.form["lastname"].lower().strip()
        email = request.form["email"].lower().strip()

        # Create a new user
        user = User()
        user.firstname = first_name
        user.lastname = last_name
        user.email = email
        user.password = generates_random_password()
        user.user_type = UserType.LIBERIAN

        # Check if user with the same email already exists
        existing_user = user.query.filter_by(email=email).first()

        if existing_user is not None:
            flash("Sorry, but a user with this email already exits!!! ")
        else:
            db.session.add(user)
            yag = yagmail.SMTP(sender_email, sender_password)
            try:
                receiver = user.email
                data = {
                    "email": user.email,
                    "send time": datetime.datetime.now(),
                    "expire time": datetime.datetime.now()+datetime.timedelta(minutes=5)
                }
                data= jsonify(data).json
                data = json.dumps(data)
                encrypted_data = encrypt_data(data, encrypt_key.encode())
                body = f"Your Account has been created, follow this link to rest your password \n http://127.0.0.1:8000/reset_password/?data={encrypted_data.decode('utf-8')}"
                # Send password reset email
                yag.send(
                    to=receiver,
                    subject="Password Reset",
                    contents=body,
                )
                db.session.commit()
            except SMTPAuthenticationError:
                return "Enoch did you follow the instructions?"

            return redirect("/librarians/")

    context = {
        "librarians": librarians,
    }

    context = {
        "librarians": librarians,
    }

    # Render the 'librarians.html' template with the librarian users
    return render_template("librarians.html", context=context)


@app.route("/librarian/<int:id>/", methods=["GET", "POST"])
@login_required
@admin_required
def librarian_detail_page(id, *args):
    """
    Display the librarian detail page and handle form submission.

    Args:
        id (int): The ID of the librarian.

    Returns:
        flask.Response: The rendered template or a redirect response.
    """

    librarian = User.query.get_or_404(id)

    if request.method == "POST":
        # Update librarian attributes based on form submission
        for key in request.form:
            if request.form[key] != "":
                if hasattr(librarian, key):
                    try:
                        setattr(librarian, str(key), request.form[key])
                    except AttributeError:
                        pass
                db.session.commit()
                return redirect(url_for("librarian_detail_page", id=id))

    if request.args.get("delete") == "true":
        # Delete the librarian if requested
        db.session.delete(librarian)
        db.session.commit()
        return redirect(url_for("get_and_create_liberian"))

    # Render the librarian detail page
    context = {
        "librarian": librarian,
    }
    return render_template("librariandetails.html", context=context)


@app.route("/librarians/", methods=["GET", "POST"])
@login_required
@admin_required
def get_librarians_and_create():
    """
    Retrieves a list of librarians or creates a new librarian.

    If the request method is POST, a new librarian is created using the form data.
    The librarian's details are validated and added to the database.
    An email is sent to the librarian with a link to reset their password.

    Returns:
        If the request method is POST and the librarian is successfully created,
        redirects to the "/librarians/" page.
        If the request method is GET, renders the "librarians.html" template with the
        list of librarians.
    """
    librarians = User.query.filter_by(user_type=UserType.LIBRARIAN).all()

    if request.method == "POST":
        # Get form data
        first_name = request.form["firstname"].lower().strip()
        last_name = request.form["lastname"].lower().strip()
        email = request.form["email"].lower().strip()

        # Create new librarian instance
        librarian = User()
        librarian.firstname = first_name
        librarian.lastname = last_name
        librarian.email = email
        librarian.password = generates_random_password()
        librarian.user_type = UserType.LIBRARIAN

        # Check if librarian with the same email already exists
        existing_librarian = librarian.query.filter_by(email=email).first()

        if existing_librarian is not None:
            flash("Sorry, but a user with this email already exists!!! ")
        else:
            db.session.add(librarian)
            yag = yagmail.SMTP(sender_email, sender_password)
            try:
                receiver = librarian.email
                data = {
                    "email": librarian.email,
                    "send time": datetime.datetime.now(),
                    "expire time": datetime.datetime.now()+datetime.timedelta(minutes=5)
                }
                data = jsonify(data).json
                data = json.dumps(data)
                encrypted_data = encrypt_data(data, encrypt_key)
                body = f"Your Account has been created, follow this link to reset your password \n http://127.0.0.1:8000/reset_password/?data={encrypted_data.decode('utf-8')}"
                yag.send(
                    to=receiver,
                    subject="Password Reset",
                    contents=body,
                )
                db.session.commit()
            except SMTPAuthenticationError:
                return "Enoch did you follow the instructions?"

            return redirect("/librarians/")

    context = {
        "librarians": librarians,
    }

    return render_template("librarians.html", context=context)


@app.route("/reset_password/", methods=["GET", "POST"])
def reset_passworded(*args, **kwargs):
    """
    Resets the user's password.

    Args:
        *args: Variable length arguments.
        **kwargs: Keyword arguments.

    Returns:
        If the password is successfully reset, redirects to the login page. Otherwise, redirects to the password reset page.

    """
    if request.args.get("data"):
        # Decrypt the data
        data = decrypt_data(request.args.get("data"), encrypt_key)
        data = json.loads(data)
        if data is not None:
            if "expire time" in data:
                current_time  = datetime.datetime.now()
                # Convert the expire time string to a datetime object
                expire_time = datetime.datetime.strptime(data["expire time"], "%a, %d %b %Y %H:%M:%S %Z")
                print(expire_time < current_time)
                if expire_time > current_time:
                    if request.method == "POST":
                        print("hello")
                        new_password = request.form.get("password")
                        # Find the user by email
                        user = User.query.filter_by(
                            email=data["email"]).first()
                        if user is not None:
                            user.is_verified = True
                            # Update the user's password
                            user.password = generates_hash_password(new_password)
                            db.session.commit()
                            return redirect(url_for("login"))
                else:
                    flash("Token has expired")
                    return redirect(url_for("login"))
                return render_template("password_reset.html")
            return redirect("/")
        return redirect("/")
    return redirect("/")


if __name__ == "__main__":
    with app.app_context():

        db.create_all()
        user = User.query.filter_by(email="admin@admin.com").first()
        if user is None:
            user = User()
            user.email = "admin@admin.com"
            user.password = generates_hash_password("admin")
            user.firstname = "admin"
            user.lastname = "admin"
            user.user_type = UserType.ADMIN
            user.is_verified = True
            db.session.add(user)
            db.session.commit()
        
    if not os.path.exists("static/student/"):
        try:
            os.makedirs("static/students/")
            print(f"Directory 'static/students/' created successfully.")
        except OSError as e:
            print(f"Error creating directory 'static/students/': {e}")
    else:
        print(f"Directory 'static/students/' already exists.")
        
        
    if not os.path.exists("static/book_qrcodes/"):
        try:
            os.makedirs("static/book_qrcodes/")
            print(f"Directory 'static/book_qrcodes/' created successfully.")
        except OSError as e:
            print(f"Error creating directory 'static/book_qrcodes/': {e}")
    else:
        print(f"Directory 'static/book_qrcodes/' already exists.")


    app.run(port=8000, debug=True , host="0.0.0.0")


# TODO check the borrow url endpoint, it is having some issues
