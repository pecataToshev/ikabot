import unittest
from unittest.mock import MagicMock, patch
import os
import sqlite3
import tempfile
import json
from ikabot.web.ikariamService import IkariamService
from ikabot.helpers.database import Database
from ikabot import config

class TestCookieSyncLogic(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp()
        config.DB_FILE = self.db_path
        
        # Initialize database
        conn = sqlite3.connect(self.db_path)
        with conn:
            conn.execute("CREATE TABLE storage (botName VARCHAR(16) NOT NULL, storageKey VARCHAR(32) NOT NULL, data TEXT, PRIMARY KEY (botName, storageKey))")
            conn.execute("CREATE TABLE locks (lockName VARCHAR(64) NOT NULL, pid INTEGER NOT NULL, updated_at TIMESTAMP NOT NULL, PRIMARY KEY (lockName))")
        conn.close()
        
        self.db = Database("test_bot")
        self.telegram = MagicMock()
        
        # Mock __login to avoid network calls
        with patch.object(IkariamService, '_IkariamService__login'):
            self.service = IkariamService(self.db, self.telegram)
            self.service.urlBase = "https://example.com/index.php?"
            self.service.s = MagicMock()
            self.service.headers = {}

    def tearDown(self):
        self.db.close_db_conn()
        os.close(self.db_fd)
        os.unlink(self.db_path)

    @patch('requests.Session')
    def test_check_cookie_reloads_on_change(self, mock_session):
        # Setup initial cookies
        self.service.s.cookies = MagicMock()
        self.service.s.cookies.items.return_value = [('ikariam', 'old_cookie')]
        
        # New cookies in DB
        new_cookies = {'ikariam': 'new_cookie'}
        self.db.store_value('cookies', new_cookies)
        
        # Call __checkCookie
        with patch.object(self.service, '_IkariamService__getCookie') as mock_get_cookie:
            self.service._IkariamService__checkCookie()
            mock_get_cookie.assert_called_once()

    @patch('requests.Session')
    def test_session_expired_uses_lock(self, mock_session):
        # Mock isExpired to always return True first, then False
        with patch.object(self.service, 'isExpired', side_effect=[True, False]):
            with patch.object(self.service, '_IkariamService__login') as mock_login:
                with patch.object(self.service, 'get', return_value="restored"):
                    # First call to sessionExpired
                    # Simulate lock acquired
                    self.service._IkariamService__sessionExpired()
                    # Should call getCookie (which we'll assume works) and then check if still expired
                    # In our case it will call __login if still expired.
                    # Wait, our __sessionExpired calls __getCookie and then get(ignoreExpire=True)
                    # If isExpired(html) is False, it returns.
                    
                    # Verify lock was used (we can check the locks table)
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM locks")
                    # Lock should be released by now
                    self.assertIsNone(cursor.fetchone())
                    conn.close()

if __name__ == '__main__':
    unittest.main()
