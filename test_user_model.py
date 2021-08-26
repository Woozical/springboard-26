"""User model tests."""

# run these tests like:
#
#    python -m unittest test_user_model.py


import os
from unittest import TestCase

from models import db, User, Message, Follows
from sqlalchemy.exc import IntegrityError

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"


# Now we can import app

from app import app

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()


class UserModelTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()
        Follows.query.delete()

        self.client = app.test_client()
    
    def tearDown(self):
        """Clean failed transactions"""
        db.session.rollback()

    def test_user_model(self):
        """Does basic model work?"""

        u = User(
            email="test@test.com",
            username="testuser",
            password="HASHED_PASSWORD"
        )

        db.session.add(u)
        db.session.commit()

        # User should have no messages & no followers
        self.assertEqual(len(u.messages), 0)
        self.assertEqual(len(u.followers), 0)
    
    def test_user_signup(self):
        """Ensure that User signup method results in new DB entry"""

        u = User.signup(
            username="testuser123",
            email="email@test.com",
            password="password123",
            image_url=None
        )

        db.session.commit()
        # User should exist with given credentials and hashed PW
        self.assertIsNotNone(User.query.get(u.id))
        self.assertIsNotNone(User.query.filter_by(username='testuser123').first())
        self.assertIsNotNone(User.query.filter_by(email='email@test.com').first())
        self.assertNotEqual(u.password, 'password123')
        self.assertEqual(u.image_url, User.image_url.default.arg)

    def test_user_notnullable_fields(self):
        # User signup with missing nullable fields should fail
        with self.assertRaises(ValueError):
            u = User.signup(
                username="testuser456",
                email="blah@email.com",
                password="",
                image_url="http://my.img/profile.jpg"
            )
            db.session.commit()
        db.session.rollback()
        
        with self.assertRaises(IntegrityError):
            u = User.signup(
                username="testuser456",
                email=None,
                password="password123",
                image_url="http://my.img/profile.jpg"
            )
            db.session.commit()
        db.session.rollback()

        with self.assertRaises(IntegrityError):
            u = User.signup(
                username=None,
                email="blah@email.com",
                password="password123",
                image_url="http://my.img/profile.jpg"
            )
            db.session.commit()
    
    def test_pw_salting(self):
        """Ensure that two users with the same password do not have the same hash."""

        u = User.signup(
            username="testUserA",
            email="email@test.com",
            password="password123",
            image_url="http://my.img/profile.jpg"
        )

        u2 = User.signup(
            username="testUserB",
            email="my_email@test.com",
            password="password123",
            image_url="http://my.img/profile.jpg"
        )

        db.session.commit()

        self.assertNotEqual(u.password, u2.password)
    
    def test_unique_constraint(self):
        """Ensure that two users cannot share the same username or email."""

        u = User.signup(
            username="testUserA",
            email="email@test.com",
            password="password123",
            image_url="http://my.img/profile.jpg"
        )
        db.session.commit()

        with self.assertRaises(IntegrityError):
            u2 = User.signup(
                username="testUserA",
                email="my_email@test.com",
                password="password123",
                image_url="http://my.img/profile.jpg"
            )
            db.session.commit()

        db.session.rollback()
        with self.assertRaises(IntegrityError):
            u3 = User.signup(
                username="testUserB",
                email="email@test.com",
                password="password123",
                image_url="http://my.img/profile.jpg"
            )
            db.session.commit()
    

    def test_user_auth_method(self):
        u = User.signup(
            username='testuser',
            email='test@test.com',
            password='password456',
            image_url=None
        )

        db.session.commit()

        self.assertEqual(
            u,
            User.authenticate('testuser', 'password456')
        )

        self.assertEqual(
            False,
            User.authenticate('testuser', 'passwor456')
        )

        self.assertEqual(
            False,
            User.authenticate('testuserr', 'password456')
        )


    def test_user_follow_methods(self):
        """Ensures functionality of User model methods that determine following/follower relationships"""

        user1 = User.signup(
            username="user1",
            email="email@test.com",
            password="password123",
            image_url="http://my.img/profile.jpg"
        )

        user2 = User.signup(
            username="user2",
            email="my_email@test.com",
            password="password123",
            image_url="http://my.img/profile.jpg"
        )

        db.session.commit()

        self.assertEqual(user1.is_following(user2), False)
        self.assertEqual(user2.is_following(user1), False)
        self.assertEqual(user2.is_followed_by(user1), False)
        self.assertEqual(user1.is_followed_by(user2), False)

        user1.following.append(user2)
        db.session.commit()

        self.assertEqual(user1.is_following(user2), True)
        self.assertEqual(user1.is_followed_by(user2), False)
        self.assertEqual(user2.is_following(user1), False)
        self.assertEqual(user2.is_followed_by(user1), True)

        user1.followers.append(user2)
        db.session.commit()

        self.assertEqual(user1.is_following(user2), True)
        self.assertEqual(user2.is_following(user1), True)
        self.assertEqual(user2.is_followed_by(user1), True)
        self.assertEqual(user1.is_followed_by(user2), True)