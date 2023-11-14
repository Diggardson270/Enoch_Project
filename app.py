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



app = Flask(__name__)
app.secret_key = "8419c249452b7241d1f7f3da3e4f9df359af0a264a988d999d408406f0976788"


basedir = os.path.abspath(os.path.dirname(__file__))

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + \
    os.path.join(basedir, 'db.sqlite3')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True


db = SQLAlchemy(app)

app = Flask(__name__)
app.secret_key = "8419c249452b7241d1f7f3da3e4f9df359af0a264a988d999d408406f0976788"


basedir = os.path.abspath(os.path.dirname(__file__))

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + \
    os.path.join(basedir, 'db.sqlite3')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True


db = SQLAlchemy(app)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
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

    # def __repr__(self):
    #     return f'<Student {self.firstname}>'

    # def __str__(self) -> str:
    #     return f'User {self.email}'





class Student(db.Model):

    # __tablename__ = "students"
    __table_args__ = (db.UniqueConstraint('matirc_number', 'user_id'), )

    id = db.Column(db.Integer, primary_key=True)
    user = db.relationship(User, lazy=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    matirc_number = db.Column(db.String(11), server_default="False", nullable=False)
    student_level = db.Column(db.Integer, nullable=False)
    books_borrowed: db.Mapped[List['BorowedBook']] = db.relationship('BorowedBook', back_populates="student", cascade="all, delete-orphan")
    bio = db.Column(db.Text)

    def __repr__(self):
        return f'<Student {self.id}>'

    def __str__(self) -> str:
        return f'User {self.id}'
    
    def borrowed(self):
        returned = list()
        not_returned = list()
        for book in  self.books_borrowed:
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
        if self.no_of_stock< 10:
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
        borrowed_books = BorowedBook.query.filter_by(book_id=self.id,is_returened=False).all()
        # return len(borrowed_books)
        return len(borrowed_books)
    
   
    


class BorowedBook(db.Model):

    # __tablename__ = "borrored-books"

    id = db.Column(db.Integer, primary_key=True)
    book = db.relationship(Book, lazy=True)
    book_id = db.Column(db.Integer, db.ForeignKey(Book.id), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey(Student.id), nullable=False)
    student = db.relationship(Student, lazy=True)
    is_returened = db.Column(db.Boolean,default=False,server_default="False", nullable=False)
    return_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    borrowed_date = db.Column(db.DateTime(timezone=True),
                           server_default=func.now())

    def __str__(self) -> str:
        return f"Hello {self.id}"
    
    @property
    def remaining_days(self):
        days_left  =  self.return_date - self.borrowed_date  
        if days_left.days<0:
            return 	"0:00:00"
        elif self.is_returened:
            return None
        return f"{days_left.days} days"
    
    @property
    def return_date_cleaned(self):
        return f"{self.return_date.year}-{self.return_date.month}-{self.return_date.day} {self.return_date.hour}:{self.return_date.minute}"
    
        
        

@app.route("/", methods=["GET", "POST"])
@login_required
def home(*args, **kwargs):
    books = Book.query.all()
    borrowed = BorowedBook.query.filter_by(is_returened=False).all()
    categories = Category.query.all()
    no_of_books = sum([i.no_of_stock for i in books])
    no_borrowed = len(BorowedBook.query.filter_by(is_returened=False).all())
    borrowed.reverse()
    recently_borrowed_books = borrowed[:6]
    average_borrowed   = 0
    most_borrowes  = 0
    others = 0
    percentage = 0
    total_borrowes = 0
    
    if len(books) > 0:
        average_borrowed = round(mean([i.no_borrowed for i in books]))
        most_borrowes = [i for i in books if i.no_borrowed > average_borrowed]
        others = sum([i.no_borrowed for i in books if i.no_borrowed< average_borrowed])
        percentage = round((no_borrowed/no_of_books)*100)
        total_borrowes = others+sum([i.no_borrowed for i in most_borrowes])
        
    
    
    
    context = {
        "recently_borrowed_books":recently_borrowed_books,
        "categories":categories,
        "len_categories": len(categories),
        "books":books[:6], 
        "no_of_books": no_of_books,
        "no_borrowed": no_borrowed,
        "percentage":percentage,
        "most_borrowed" :most_borrowes,
        "others":others,
        "total_borrowes": total_borrowes
    }
    return render_template("index.html", context=context)

@app.route("/books/", methods=["GET", "POST"])
@login_required
def get_and_create_books():
    authors = Author.query.all()
    books = Book.query.all()
    categories = Category.query.all()
    if request.method == "POST":
        title = request.form["book_title"]
        author = request.form["book_author"]
        category_id = request.form["book_category"]
        stock = request.form["no_in_stock"]

        book = Book()
        book.author_id = author
        book.title = title.lower().strip()
        book.category_id = category_id
        book.no_of_stock = stock
        
        existing_book_title = Book.query.filter_by(title=book.title).first()
        
        
        if existing_book_title:
            flash("Sorry, but this title already exits!!! ")
        else:
            title = book.title.replace(" ", "-").lower().strip()
            qr_dir = f"book_qrcodes/{book.slug}.png"
            db.session.add(book)
            db.session.commit()
            data = {
                "title": book.title,
                "author_id": book.author_id,
                "author_firstname": book.author.firstname,
                "author_lastname": book.author.lastname,
                "category_id": book.category_id,
                "category_name": book.category.name
            }
            book_qrcode = qrcode.make(data=data, box_size=4, border=5)
            book_qrcode.save(f"static/{qr_dir}")
            return redirect("/books/")

    context = {
        "authors": authors,
        "books": books,
        "categories": categories
    }

    return render_template("books.html", context=context)


@app.route("/book/<int:id>/", methods=["GET", "POST"])
@login_required
def book_detail_page(id , *args, **kwargs):
    book = Book.query.get_or_404(id)
    qr_code = book.slug
    authors = Author.query.all()
    categories = Category.query.all()
    
    borrowed_books = BorowedBook.query.filter_by(book_id=id).all()
    if request.method == "POST":
        print(book.author_id)
        for key in request.form:
            if request.form[key] != "":
                existing_book_title = Book.query.filter_by(title=request.form["title"]).first()
                if existing_book_title:
                    flash("Sorry, but this title already exits!!! ")
               
                else:
                    if hasattr(book, key):
                            try:
                                setattr(book, str(key), request.form[key])
                            except AttributeError:
                                pass
                            print(book.author_id)
                    qr_dir = f"book_qrcodes/{book.slug}.png"
                    data = {
                        "title": book.title,
                        "author_id": book.author_id,
                        "author_firstname": book.author.firstname,
                        "author_lastname": book.author.lastname,
                        "category_id": book.category_id,
                        "category_name": book.category.name
                    }
                    book_qrcode = qrcode.make(data=data, box_size=4, border=5)
                    book_qrcode.save(f"static/{qr_dir}")
                    db.session.commit()
                    return redirect(url_for("book_detail_page", id=id))
    if request.args.get("delete") == "true":
        borrowed_books = BorowedBook.query.filter_by(book_id=book.id)
        for borroewd in borrowed_books:
            db.session.delete(borroewd)
        db.session.delete(book)
        db.session.commit()
        return redirect(url_for("get_and_create_books"))
    if request.args.get("returned") == "true":
        borrowed_book = BorowedBook.query.get_or_404(request.args.get("id"))
        if borrowed_book:
            print(str(borrowed_book))
            borrowed_book.is_returened = True
            book.no_of_stock += 1
            db.session.commit()
            return redirect(url_for("book_detail_page", id=id))
        
    elif request.args.get("returned") == "false":
        borrowed_book = BorowedBook.query.get_or_404(request.args.get("id"))
        if borrowed_book:
            print(str(borrowed_book))
            borrowed_book.is_returened = False
            book.no_of_stock -= 1
            db.session.commit()
            return redirect(url_for("book_detail_page", id=id))
    
    context = {
        "book": book,
        "authors": authors,
        "categories": categories,
        "borrowed_books": borrowed_books,
        "qr_code": url_for('static', filename=f"book_qrcodes/{qr_code}.png"),
    }
    return render_template("bookdetails.html", context=context)


    


@app.route("/students/", methods=["GET", "POST"])
@login_required
def get_and_create_student():
    students = Student.query.all()
    if request.method == "POST":
        first_name = request.form["first_name"]
        last_name = request.form["last_name"].lower().strip()
        email = request.form["email"]
        level = request.form["student_level"]
        matric_number = request.form["matric_number"].lower().strip()
        
        user = User()
        user.firstname = first_name.lower().strip()
        user.lastname = last_name.lower().strip()
        user.email = email
        user.password = "nill"
        user.user_type = UserType.STUDENT
        
        
        existing_user_email = user.query.filter_by(email=user.email).first()
        existing_user_matric_number = Student.query.filter_by(matirc_number=matric_number).first()
        
        if existing_user_email or existing_user_matric_number:
            if existing_user_email:
                flash("Sorry, but this email already exits!!! ")
            if existing_user_matric_number:
                 flash("Sorry, but this matric number already exits!!! ")
        else:
            fullname = f"{user.firstname} {user.lastname}".title().strip()
            qr_dir = f'students/{fullname.lower().replace(" ", "-")}.png'
            db.session.add(user)
            db.session.flush()
            student = Student()
            student.user_id = user.id
            student.student_level = level
            student.matirc_number = matric_number

            
            data = {
                "user id":user.id,
                "name":fullname,
                "email":user.email,
                "level":student.student_level
            }
            student_qrcode = qrcode.make(data=data, box_size=4, border=5)
            student_qrcode.save(f"static/{qr_dir}")
            db.session.add(student)
            db.session.commit()
            return redirect("/students/")

    context = {
        "students": students,
        "levels":StudentLevel
    }
    

    return render_template("students.html", context=context)




@app.route("/student/<int:id>/", methods=["GET", "POST"])
@login_required
def student_detail_page(id, *args):
    student = Student.query.get_or_404(id)
    user = User.query.get_or_404(student.user_id)
    fullname = f"{student.user.firstname} {student.user.lastname}".title().strip()
    qr_code = f'{fullname.lower().replace(" ", "-")}.png'
    previous_first_name = user.firstname
    previous_last_name = user.lastname
    previous_fullname = f"{previous_first_name} {previous_last_name}".title().strip()
    previous_qr_dir = f'static/students/{previous_fullname.lower().replace(" ", "-")}.png'   
    
    borrowed_books = BorowedBook.query.filter_by(student_id=id).all()
    if request.method == "POST":
        for key in request.form:
            if request.form[key] != "":
             
   
                existing_user_email = user.query.filter_by(email=request.form["email"]).first()
                existing_user_matric_number = Student.query.filter_by(matirc_number=request.form["matirc_number"]).first()
                
                
                if existing_user_email:
                    flash("Sorry, but this email already exits!!! ")
                if existing_user_matric_number:
                    flash("Sorry, but this matric number already exits!!! ")
                else:
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
                    os.remove(os.path.join(basedir, previous_qr_dir))
                    fullname = f"{user.firstname} {user.lastname}".title().strip()
                    qr_dir = f'students/{fullname.lower().replace(" ", "-")}.png'   
                    data = {
                        "user id":user.id,
                        "name":fullname,
                        "email":user.email,
                        "level":student.student_level,
                        "matric_number":student.matirc_number
                    }
                    student_qrcode = qrcode.make(data=data, box_size=4, border=5)
                    student_qrcode.save(f"static/{qr_dir}")
                    db.session.commit()
                    return redirect(url_for("student_detail_page", id=id))
    if request.args.get("delete") == "true":
        borrowed_books = BorowedBook.query.filter_by(student_id=student.id)
        for borroewd in borrowed_books:
            db.session.delete(borroewd)
        db.session.delete(student)
        db.session.delete(user)
        db.session.commit()
        return redirect(url_for("get_and_create_student"))
        
    
    context = {
        "student": student,
        "qr_code": url_for('static', filename=f"students/{qr_code}"),
        "levels":StudentLevel
    }
    return render_template("studentdetails.html", context=context)



@app.route('/qrcode/<path:filename>/')
def download_file(filename:str):
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
    if request.args.get("user_id") and request.args.get("book_title"):
        session.pop("user_id", None)
        student = Student.query.filter_by(user_id = request.args.get("user_id")).first()
        book = Book.query.filter_by(title = request.args.get("book_title")).first()
        
        if student and book:
            if request.method == "POST":
                borrow_book = BorowedBook()
                borrow_book.book_id = book.id
                borrow_book.student_id = student.id
                db.session.add(borrow_book)
                db.session.commit()
                return redirect(url_for("home"))
        context = {
            "student": student,
            "book":book,
            "no_of_pending_books": len([book for book in student.books_borrowed if book.is_returned == False])
        }
        return render_template("book_qrcode_submit.html", context=context)
        
    elif request.args.get("user_id") is not None:
        
        student = Student.query.filter_by(user_id = request.args.get("user_id")).first()
        if student:
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
    categories = Category.query.all()
    if request.method == "POST":
        name = request.form["name"].lower().strip()
        
        category = Category()
        category.name = name
        
        
        existing_category_name = category.query.filter_by(name=category.name).first()
        
        if existing_category_name:
            flash("Sorry, but this category already exits!!! ")
        else:
            db.session.add(category)
            db.session.commit()
            return redirect("/categories/")
    

    context = {
        "categories": categories,
    }
    

    return render_template("categories.html", context=context)



@app.route("/category/<int:id>/",  methods=["GET", "POST"])
@login_required
def category_detail_page(id, *args, **kwargs):
    category = Category.query.get_or_404(id)
    
    if request.method == "POST":
        for key in request.form:
            if request.form[key] != "":
        
                existing_category_name = category.query.filter_by(name=request.form["name"]).first()
                if existing_category_name:
                    flash("Sorry, but this matric number already exits!!! ")
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


@app.route("/authors/", methods=["GET", "POST"])
@login_required
def get_and_create_author():
    authors = Author.query.all()
    if request.method == "POST":
        first_name = request.form["firstname"].lower().strip()
        last_name = request.form["lastname"].lower().strip()
        
        author = Author()
        author.firstname = first_name
        author.lastname = last_name
        
        
        existing_author = author.query.filter_by(firstname=first_name, lastname=last_name).first()
        
        if existing_author:
            flash("Sorry, but this author already exits!!! ")
        else:
            db.session.add(author)
            db.session.commit()
            return redirect("/authors/")
    context = {
        "authors": authors,
    }
    
    return render_template("author.html", context=context)



@app.route("/author/<int:id>/", methods=["GET", "POST"])
@login_required
def author_detail_page(id, *args):
    author = Author.query.get_or_404(id)
    
    if request.method == "POST":
        
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
        db.session.delete(author)
        db.session.commit()
        return redirect(url_for("get_and_create_author"))
    context = {
        "author": author,
    }
    return render_template("authordetails.html", context=context)


@app.route("/user/", methods=["GET", "POST"])
def detail_page(*args):
    return render_template("user.html")


@app.route("/user/settings/", methods=["GET", "POST"])
def user_settings_page(*args, **kwargs):
    inputs_data = {}
    new_session =  session["user"].copy()
    user = User.query.filter_by(email=session["user"]["email"]).first()
    if request.method == "POST":
        if request.form.get("firstname")!= "" or request.form.get("lastname")!= "" or request.form.get("emailaddress") != "" or request.form.get("newpassword") != "":
            if request.form.get("firstname"):
                firstname = request.form.get("firstname")
                inputs_data["firstname"] = firstname
            if request.form.get("lastname"):
                lastname = request.form.get("lastname")
                inputs_data["lastname"] = lastname
            if request.form.get("emailaddress"):
                email = request.form.get("emailaddress")
                password = request.form.get("confirmemailpassword")
                if not check_password(password, user.password):
                    flash("Invalid Password")
                inputs_data["email"] = email
                
                    
            if request.form.get("newpassword"):
                newpassword = request.form.get("newpassword")
                confirmpassword = request.form.get("confirmpassword")
                currentpassword = request.form.get("currentpassword")
                
                if newpassword != confirmpassword:
                    flash("Invalid Password")
                
                if not check_password(currentpassword, user.password):
                    flash("Invalid Password")
                inputs_data["password"] = generates_hash_password(newpassword)
            
            for key in inputs_data:
                if hasattr(user, key):
                    setattr(user, key, inputs_data[key])
            
            db.session.commit()
            
            for key in new_session:
                if key in inputs_data:
                    new_session[key] = inputs_data[key]
                
            session["user"] = new_session
            
        return redirect(url_for("user_settings_page"))
            
    return render_template("user_settings.html")



@app.route("/login/", methods=["GET", "POST"])
def login(*args, **kwargs):
    if request.method =="POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user= User.query.filter_by(email=email).first()
        if check_password(password, user.password):
            logged = LoggedIn(**{field:vars(user).get(field) for field in vars(user) if field in vars(LoggedIn)})
            session["user"] = vars(logged)
            return redirect(url_for("home"))
        flash("Invalid email or password", category=  "warning")
    return render_template("login.html")



@app.route("/logout/")
@login_required
def logout(*args, **kwargs):
    session.pop("user", None)
    return redirect(url_for("login"))


@app.route("/forgot_password/", methods=["GET", "POST"])
def forgot_password(*args, **kwargs):
    return render_template("forgot_password.html")


@app.route("/password_reset/", methods=["GET", "POST"])
def password_reset(*args, **kwargs):
    return render_template("password_reset.html")


@app.route("/json_categories/", methods=["GET"])
def request_categories():
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
    return render_template("scan.html")


@app.route("/clean_data/", methods=["GET", "POST"])
def clean_and_return_id(*args, **kwargs):
    data = request.args.get("data").strip()
    result = ast.literal_eval(data)
    if "title" in result:
        return redirect(f"/borrow/borrow_with_qr/?user_id={session['user_id']}&book_title={result['title']}")
    return redirect(f"/borrow/borrow_with_qr/?user_id={result['user id']}")

def check_password(enterd_password:str, hash_password:bytes):
    
    enterd_password_hash = enterd_password.encode("utf-8")
    
    return bcrypt.checkpw(enterd_password_hash, hash_password)
    
    
def generates_hash_password(enterd_password:str):
    
    enterd_password_hash = enterd_password.encode("utf-8")
    salt = bcrypt.gensalt()
    
    password_hash = bcrypt.hashpw(enterd_password_hash, salt)
    
    return password_hash
    
    
    
    
def generates_random_password():
    pass


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
            db.session.add(user)
            db.session.commit()

    app.run(port=8000, debug=True)#, host="0.0.0.0")




#TODO check the borrow url endpoint, it is having some issues