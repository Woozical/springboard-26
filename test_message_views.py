"""Message View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_message_views.py


import os
from unittest import TestCase

from models import db, connect_db, Message, User

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"


# Now we can import app

from app import app, CURR_USER_KEY

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()

# Don't have WTForms use CSRF at all, since it's a pain to test

app.config['WTF_CSRF_ENABLED'] = False


class MessageViewTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()

        self.client = app.test_client()

        self.testuser = User.signup(username="testuser",
                                    email="test@test.com",
                                    password="testuser",
                                    image_url=None)

        db.session.commit()

        testmsg = Message(text="Testing Message", user_id = self.testuser.id)

        db.session.add(testmsg)
        db.session.commit()

        self.msg_id = testmsg.id
    
    def tearDown(self):
        """Clean failed transactions"""
        db.session.rollback()

    def test_add_message(self):
        """Ensure user can add a message"""

        # Since we need to change the session to mimic logging in,
        # we need to use the changing-session trick:

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            # Now, that session setting is saved, so we can have
            # the rest of ours test

            resp = c.post("/messages/new", data={"text": "Hello"})

            # Make sure it redirects
            self.assertEqual(resp.status_code, 302)

            msg = Message.query.filter_by(user_id=self.testuser.id).filter_by(text="Hello").first()
            self.assertIsNotNone(msg)

            # Ensure we see our message in the user page
            resp = c.get(f'/users/{self.testuser.id}')
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('Hello', html)

            # Ensure we our message exists in its route
            resp = c.get(f'/messages/{msg.id}')
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn('Hello', html)
            self.assertIn(self.testuser.username, html)
    
    def test_new_message_view(self):
        """Ensure we receive our form when hitting new message route"""

        with self.client as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id
            res = client.get('/messages/new')
            html = res.get_data(as_text=True)

            self.assertEqual(res.status_code, 200)
            self.assertIn('form', html)
            self.assertIn('method="POST"', html)
    
    def test_show_message_view(self):
        """Ensure we can see our message"""
        with self.client as client:
            res = client.get(f'messages/{self.msg_id}')
            html = res.get_data(as_text=True)

            self.assertEqual(res.status_code, 200)
            self.assertIn('Testing Message', html)

    def test_delete_message(self):
        """Ensure message is deleted on hitting route"""

        with self.client as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id
            
            URL = f'/messages/{self.msg_id}/delete'
            # Ensure we cannot GET the route
            res = client.get(URL)
            self.assertEqual(res.status_code, 405)
            
            res = client.post(URL)
            self.assertEqual(res.status_code, 302)
            self.assertIsNone(Message.query.get(self.msg_id))

    def test_unauth_delete_message(self):
        """Ensure a logged-in user cannot delete other's messages"""

        with self.client as client:
            with client.session_transaction() as sess:
                new_user = User.signup(username='jimbo', email='test@jimbo.com', password='password123', image_url=None)
                db.session.commit()
                sess[CURR_USER_KEY] = new_user.id
            
            URL = f'/messages/{self.msg_id}/delete'

            res = client.post(URL, follow_redirects=True)
            html = res.get_data(as_text=True)

            self.assertEqual(res.status_code, 200)
            self.assertIn('unauthorized', html)

class UnAuthMessageViewTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()

        self.client = app.test_client()

        self.testuser = User.signup(username="testuser",
                                    email="test@test.com",
                                    password="testuser",
                                    image_url=None)

        db.session.commit()

        testmsg = Message(text="Testing Message", user_id = self.testuser.id)

        db.session.add(testmsg)
        db.session.commit()

        self.msg_id = testmsg.id
    
    def tearDown(self):
        """Clean failed transactions"""
        db.session.rollback()
    
    def test_add_message(self):
        """Ensure un-authenticated users cannot add new messages"""

        with self.client as client:
            # Cannot POST
            res = client.post("/messages/new", data={"text": "Hello"}, follow_redirects=True)
            html = res.get_data(as_text=True)

            self.assertEqual(res.status_code, 200)
            self.assertIn('unauthorized', html)

            # Redirect on GET
            res = client.get('/messages/new', follow_redirects=True)
            html = res.get_data(as_text=True)

            self.assertEqual(res.status_code, 200)
            self.assertIn('unauthorized', html)
    
    def test_delete_message(self):
        """Ensure un-authenticated users cannot delete messages"""

        with self.client as client:
            URL = f"/messages/{self.msg_id}/delete"
            # Cannot POST
            res = client.post(URL, follow_redirects=True)
            html = res.get_data(as_text=True)

            self.assertEqual(res.status_code, 200)
            self.assertIn('unauthorized', html)

            # GET not allowed
            res = client.get(URL)
            self.assertEqual(res.status_code, 405)