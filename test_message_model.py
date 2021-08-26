"""Message model tests."""

import os
from unittest import TestCase

from models import db, User, Message, Follows
from sqlalchemy.exc import IntegrityError, DataError

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"

from app import app

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()

class MessageModelTestCase(TestCase):

    def setUp(self):
        """Clear db and create sample data"""
        User.query.delete()
        Follows.query.delete()
        Message.query.delete()

        u = User(
            username="testuser",
            email="test@test.com",
            password="pw_hash"
        )

        db.session.add(u)
        db.session.commit()

        m = Message(
            text="This is a test message.",
            user_id = u.id
        )

        db.session.add(m)
        db.session.commit()

        self.message_id = m.id
        self.user_id = u.id

    def tearDown(self):
        """Clean failed transactions"""
        db.session.rollback()

    
    def test_message_model(self):
        """Ensure that new message exists in DB"""
        m = Message.query.get(self.message_id)
        self.assertIsNotNone(m)
        self.assertIsNotNone(m.timestamp)
        
    def test_message_user_relationship(self):
        """Ensure integrity of Message <-> User relationship"""
        m = Message.query.get(self.message_id)
        self.assertEqual(
            m.user,
            User.query.get(self.user_id)
        )

        self.assertEqual(m.user.username, 'testuser')
        self.assertEqual(m.user.email, 'test@test.com')
    
    def test_message_FK_deletion_cascade(self):
        """Ensure cascade when User is deleted"""

        User.query.filter_by(id=self.user_id).delete()
        db.session.commit()

        self.assertIsNone(Message.query.get(self.message_id))
    
    def test_message_constraints(self):
        """Ensure message column constraints"""

        # Text should be < 140 characters
        text = ""
        while (len(text) < 200):
            text = text + "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        
        with self.assertRaises(DataError):
            m = Message(
                text = text,
                user_id = self.user_id
            )
            db.session.add(m)
            db.session.commit()
        
        db.session.rollback()

        # Text must not be null
        with self.assertRaises(IntegrityError):
            m = Message(
                user_id = self.user_id
            )
            db.session.add(m)
            db.session.commit()
       
        db.session.rollback()
       
        # User ID must not be null
        with self.assertRaises(IntegrityError):
            m = Message(text="Hello world")
            db.session.add(m)
            db.session.commit()
        
        db.session.rollback()

        # User ID must correspond to existing user
        with self.assertRaises(IntegrityError):
            m = Message(text="Hello World", user_id = (self.user_id * 2))
            db.session.add(m)
            db.session.commit()
    