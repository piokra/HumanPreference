# models.py

from flask_login import UserMixin
from . import db

owners_association_table = db.Table('owners_association', db.Model.metadata,
                                    db.Column('left_id', db.Integer, db.ForeignKey('user.id')),
                                    db.Column('right_id', db.Integer, db.ForeignKey('project.id'))
                                    )

authorized_association_table = db.Table('authorized_association', db.Model.metadata,
                                        db.Column('left_id', db.Integer, db.ForeignKey('user.id')),
                                        db.Column('right_id', db.Integer, db.ForeignKey('project.id'))
                                        )


class User(UserMixin, db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)  # primary keys are required by SQLAlchemy
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))


class Project(db.Model):
    __tablename__ = 'project'

    id = db.Column(db.Integer, primary_key=True)  # primary keys are required by SQLAlchemy
    name = db.Column(db.String(100), unique=True)
    description = db.Column(db.String(1000))

    owners = db.relationship("User", secondary=owners_association_table)
    authorized_users = db.relationship("User", secondary=authorized_association_table)
