from . import db, login_manager
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, LoginManager, current_user, AnonymousUserMixin
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app, request
from markdown import markdown
import bleach, hashlib

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True, index = True)
    username = db.Column(db.String(64), unique=True, index = True)
    password_hash = db.Column(db.String(128))
    admin = db.Column(db.Boolean, default=False)
    avatar_hash = db.Column(db.String(64))
    create_at = db.Column(db.DateTime, default=datetime.utcnow)
    blogs = db.relationship('Blog', backref='author', lazy= 'dynamic')
    comments = db.relationship('Comment', backref='author', lazy= 'dynamic')

    def __init__(self, **kw):
        super(User, self).__init__(**kw)
        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash = hashlib.md5(self.email.encode('utf-8')).hexdigest()

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_administrator(self):
        return self.admin

    # 生成Gravatar头像
    def gravatar(self, size=100, default='identicon', rating='g'):
        if request.is_secure:
            url = 'https://secure.gravatar.com/avatar'
        else:
            url = 'http://www.gravatar.com/avatar'
        hash = self.avatar_hash or hashlib.mp5(self.email.encode('utf-8')).hexdigest()
        return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
            url=url, hash=hash, size=size, default=default, rating=rating)

    @staticmethod
    def generate_fake(count=100):
        from sqlalchemy.exc import IntegrityError
        from random import seed
        import forgery_py

        seed()
        for i in range(count):
            u = User(email = forgery_py.internet.email_address(),
                     username = forgery_py.internet.user_name(True),
                     password = forgery_py.lorem_ipsum.word(),
                     admin = False)
            db.session.add(u)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()

class AnonymousUser(AnonymousUserMixin):
    def is_administrator(self):
        return False

login_manager.anonymous_user = AnonymousUser

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Blog(db.Model):
    __tablename__ = 'blogs'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    summary = db.Column(db.Text)
    summary_html = db.Column(db.Text)
    content = db.Column(db.Text)
    content_html = db.Column(db.Text)
    create_at = db.Column(db.DateTime, default=datetime.utcnow, index = True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    comments = db.relationship('Comment', backref='blog', lazy= 'dynamic')

    @staticmethod
    def on_changed_summary(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
                        'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
                        'h1', 'h2', 'h3', 'p']
        target.summary_html = bleach.linkify(bleach.clean(
            markdown(value, output_format = 'html'), 
            tags = allowed_tags, strip = True))

    @staticmethod
    def on_changed_content(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
                        'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
                        'h1', 'h2', 'h3', 'p']
        target.content_html = bleach.linkify(bleach.clean(
            markdown(value, output_format = 'html'), 
            tags = allowed_tags, strip = True))

    @staticmethod
    def generate_fake(count=100):
        from random import seed, randint
        import forgery_py
        u = User.query.filter_by(id=1).first()

        seed()
        for i in range(count):
            try:
                b = Blog(name = forgery_py.lorem_ipsum.sentences(1),
                         summary = forgery_py.lorem_ipsum.sentences(randint(3,5)),
                         content = forgery_py.lorem_ipsum.sentences(randint(8,10)),
                         create_at = forgery_py.date.date(True),
                         author = u)
                db.session.add(b)
                db.session.commit()
            except AttributeError:
                pass    



db.event.listen(Blog.summary, 'set', Blog.on_changed_summary)
db.event.listen(Blog.content, 'set', Blog.on_changed_content)

class Comment(db.Model):
    __tablename__ = 'comments'

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text)
    create_at = db.Column(db.DateTime, default=datetime.utcnow, index = True)
    disabled = db.Column(db.Boolean, default=False)
    blog_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    author_id = db.Column(db.Integer, db.ForeignKey('blogs.id'))

    @staticmethod
    def generate_fake(count=100):
        from random import seed, randint
        import forgery_py

        seed()
        user_count = User.query.count()
        blog_count = Blog.query.count()
        for i in range(count):
            u = User.query.offset(randint(0, user_count - 1)).first()
            b = Blog.query.offset(randint(0, blog_count - 1)).first()
            c = Comment(content = forgery_py.lorem_ipsum.sentences(randint(1, 2)),
                        create_at = forgery_py.date.date(True),
                        disabled = False,
                        author = u,
                        blog = b)
            db.session.add(c)
            db.session.commit()