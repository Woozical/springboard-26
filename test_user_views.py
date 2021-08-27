"""User View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_message_views.py


import os
from unittest import TestCase

from models import db, connect_db, Message, User, Follows

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"


# Now we can import app

from app import app, CURR_USER_KEY, session

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data
db.drop_all()
db.create_all()

# Don't have WTForms use CSRF at all, since it's a pain to test

app.config['WTF_CSRF_ENABLED'] = False


class UserViewTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()
        Follows.query.delete()

        self.client = app.test_client()

        self.testuser = User.signup(username="testuser",
                                    email="test@test.com",
                                    password="testuser",
                                    image_url=None)

        self.other_user = User.signup(username="jimbo", email="jimbo@jimbo.com", password="password", image_url=None)

        db.session.commit()
        self.testuser.following.append(self.other_user)
        testmsg = Message(text="Testing Message", user_id = self.testuser.id)
        testmsg2 = Message(text="Hello World", user_id = self.other_user.id)
        db.session.add_all([testmsg, testmsg2])
        db.session.commit()

        self.test_user_id = self.testuser.id
        self.other_user_id = self.other_user.id
        self.msg_id = testmsg.id
    
    def tearDown(self):
        """Clean failed transactions"""
        db.session.rollback()

    
    def test_home_view(self):
        """Ensure we get correct HTML for homepage"""
        with self.client as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id
            
            
            res = client.get('/')
            html = res.get_data(as_text=True)

            self.assertEqual(res.status_code, 200)
            self.assertIn('Testing Message', html) # Should show our own messages
            self.assertIn('Hello World', html) # Should show messages of followed users

            # Should show notification if no messages
            Message.query.delete()
            db.session.commit()

            res = client.get('/')
            html = res.get_data(as_text=True)

            self.assertEqual(res.status_code, 200)
            self.assertIn('no messages', html)


    def test_user_index(self):
        """Ensure we get a list of all users"""
        with self.client as client:
            res = client.get('/users')
            html = res.get_data(as_text=True)

            self.assertEqual(res.status_code, 200)
            self.assertIn(self.testuser.username, html)
            self.assertIn(self.other_user.username, html)
    
    def test_user_profile(self):
        """Ensure we get proper HMTL for user profile"""
        with self.client as client:
            res = client.get(f'/users/{self.other_user.id}')
            html = res.get_data(as_text=True)

            self.assertEqual(res.status_code, 200)
            self.assertIn(self.other_user.username, html)
            self.assertIn('Hello World', html)

            # Should return 404 on non-valid user id in route
            res = client.get('/users/9001')
            self.assertEqual(res.status_code, 404)
    
    def test_following_view(self):
        """Ensure we get proper HTML for a list of users a user is following"""
        with self.client as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            res = client.get(f'/users/{self.testuser.id}/following')
            html = res.get_data(as_text=True)

            followed_user = User.query.get(self.other_user_id)

            self.assertEqual(res.status_code, 200)
            self.assertIn(followed_user.username, html)
    
    def test_followers_view(self):
        """Ensure we get proper HTML for a list of user's followers"""
        with self.client as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id
            
            res = client.get(f'/users/{self.other_user.id}/followers')
            html = res.get_data(as_text=True)

            self.assertEqual(res.status_code, 200)
            self.assertIn(self.testuser.username, html)

    def test_change_following(self):
        """Ensure POST routes for starting/stopping to follow a user work"""
        with self.client as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id
            
            res = client.post(f'/users/stop-following/{self.other_user.id}')

            # Should redirect
            self.assertEqual(res.status_code, 302)
            # Change should reflect in DB
            self.assertEqual(Follows.query.all(), [])


            res = client.post(f'/users/follow/{self.other_user.id}')
            # Should redirect
            self.assertEqual(res.status_code, 302)
            # Change should reflect in DB
            self.assertNotEqual(Follows.query.all(), [])

            # Should return 404 on invalid user id
            res = client.post(f'/users/follow/9001')
            self.assertEqual(res.status_code, 404)
    
    def test_edit_profile_view(self):
        """Ensure we get a form for editing the user's profile"""
        with self.client as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id
            
            res = client.get('/users/profile')
            html = res.get_data(as_text=True)

            self.assertEqual(res.status_code, 200)
            self.assertIn('<form', html)
            self.assertIn('method="POST"', html)
            self.assertIn(f'value="{self.testuser.username}"', html)

    def test_edit_profile_post(self):
        """Ensure user editing form is validated by password and updates user info in db"""
        with self.client as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id
            
            
            data = {
                'username' : 'testuser',
                'email' : 'test@test.com',
                'image_url' : 'http://newimage.com/image.jpg',
                'header_image_url' : User.header_image_url.default.arg,
                'bio' : 'My new bio',
                'location' : '',
                'password' : 'testuser'
            }

            res = client.post('/users/profile', data=data)
            # Should redirect
            self.assertEqual(res.status_code, 302)
            # Should update
            updated = User.query.get(self.test_user_id)
            self.assertEqual(updated.image_url, data['image_url'])

            ### With incorrect password
            data = {
                'username' : 'testuser',
                'email' : 'test@test.com',
                'image_url' : 'http://newimage.com/failed.jpg',
                'header_image_url' : User.header_image_url.default.arg,
                'bio' : 'My new bio',
                'location' : '',
                'password' : 'incorrectPassword'
            }

            res = client.post('/users/profile', data=data)
            # Should redirect
            self.assertEqual(res.status_code, 302)
            # Should NOT update
            self.assertNotEqual(updated.image_url, data['image_url'])
    

    ## This test is oddly failing. When the route is hit with my test, SQL alchemy isn't doing a delete cascade on messages
    # Note the delete cascade works when browsing, and on model tests
    # It appears to be an issue with the route's view function using the following method:
    # db.session.delete(g.user)
    # If the view function deletes the record in the following manner, the test passes:
    # User.query.filter_by(id = g.user.id).delete()
    def test_user_deletion(self):
        with app.test_client() as client:
            # Preps the Flask session cookie before test client makes the request
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id # Sets the Flask Session Cookie <SecureCookieSession {'curr_user': self.testuser.id}>
            
            # Client is logged in... ('curr_user' in session cookie)
            client.get('/')
            self.assertIn(CURR_USER_KEY, session)

            res = client.post('/users/delete')
            #should logout user, aka Delete 'curr_user' from session cookie
            self.assertNotIn(CURR_USER_KEY, session)

            # should delete user from DB
            self.assertIsNone(User.query.get(self.testuser.id))

            # should redirect
            self.assertEqual(res.status_code, 302)

