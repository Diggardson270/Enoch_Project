from cgi import print_arguments
import os
from flask import Flask, render_template, request, url_for, redirect, send_file, Response, session, flash, get_flashed_messages
from flask_sqlalchemy import SQLAlchemy
from typing import List
from sqlalchemy.sql import func
from sqlalchemy.orm.decl_api import DeclarativeMeta
from enum import StrEnum, Enum
import datetime
import qrcode
import secrets
import json
import ast
import math



app = Flask(__name__)
app.secret_key = "8419c249452b7241d1f7f3da3e4f9df359af0a264a988d999d408406f0976788"


basedir = os.path.abspath(os.path.dirname(__file__))

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + \
    os.path.join(basedir, 'db.sqlite3')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True


db = SQLAlchemy(app)
main_ref_code = None






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


class User(db.Model):

    # __tablename__ = "user"
    __table_args__ = (db.UniqueConstraint('email'), )

    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(100), nullable=False)
    lastname = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(80), unique=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now())
    bio = db.Column(db.Text)
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
        return f"{days_left.days} days"
    
    @property
    def return_date_cleaned(self):
        return f"{self.return_date.year}-{self.return_date.month}-{self.return_date.day} {self.return_date.hour}:{self.return_date.minute}:{self.return_date.second}"
    
        
        

# @app.route("/", methods=["GET", "POST"])
# def home(*args, **kwargs):
#     return "Hello"

@app.route("/books/", methods=["GET", "POST"])
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
def borrow_book(*args, **kwargs):
    selection = []
    students = Student.query.all()
    books = Book.query.all()
    categories = Category.query.all()
    selected_students = []
    selected_books = []
    not_found = []
    not_enough_in_stock = []
    if request.args:
        if request.args.get("submit_method")== "use_qr_code":
            return "True"
        else:
            if request.args.get("submit_method")== "input_manually":
            
                if request.method =="POST": 
                    length = len(request.form)
                    selection = return_student_and_books(request.form, length)
                    session_selection = []
                    for i in selection:
                        session_selection.append([i[0], str(i[1])])
                    session["selection"] = session_selection
                    for _book_id, _students in selection:
                        selected_books.extend([book for book in books if book.id == _book_id])
                        # for book in books:
                        #     if book.id == _book_id:
                        #         if book.no_of_stock < len(_students):
                        #             not_enough_in_stock.append(book)
                        #         else:
                        #             selected_books.append(book)
                            
                        for student in students:  
                            for index, matric_number in enumerate(_students):
                                if matric_number == student.matirc_number:
                                    selected_students.append(student)
                                    _students.pop(index)
                                    if matric_number in not_found:
                                        not_found.remove(matric_number)
                                    break
                                not_found.append(matric_number)  
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
                for i in session["selection"]:
                    students = ast.literal_eval(i[1])
                    book_id = i[0]
                    borrowed_book = BorowedBook()
                    for matirc_number in students:
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



@app.route("/categories/", methods=["GET", "POST"])
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

def remove_more_than_one_occurance(item):
    new_list = []
    for x in item:
        if x not in new_list:
            new_list.append(x)
        else:
            continue
    return new_list
        

def return_student_and_books(to_sort, length):
    to_sort = dict(to_sort)
    main_list = []
    def recursive_cursive(form_list, counter):
        to_pop2 = 0
        if counter != 0:
            try:
                index = int(list(form_list.keys())[counter-1])
                for j in to_sort.keys():
                    if j == str(index):
                        pass
                    else:
                        to_pop2 = j
                        matric_number = j.split("_")
                        if matric_number[0] == str(index):
                            new_list = [index, to_sort[j]]
                            main_list.append(new_list)
                            break
                form_list.pop(str(index))
                form_list.pop(to_pop2)
            except ValueError:
                pass
            counter -=1                    
            recursive_cursive(form_list, counter)
    recursive_cursive(to_sort, length)
    for j, selectioned in enumerate(main_list):
        names = selectioned[1].split(",")
        for i, x in enumerate(names):
            x = x.strip()
            names[i] = x
        new_list = [selectioned[0], names]
        main_list[j] = new_list
    return main_list

if __name__ == "__main__":
    with app.app_context():

        db.create_all()

    app.run(port=8000, debug=True)




#TODO check the borrow url endpoint, it is having some issues