<?php
// Start session for auth
if (session_status() === PHP_SESSION_NONE) {
    session_start();
}

// Base URL (no trailing slash). Update this on production:
define('BASE_URL', 'https://dhrubfoundation.org'); 
// For local dev, you could use: 'http://localhost/dhrub-foundation'

// Simple admin credentials (change these!)
define('ADMIN_USER', 'admin@dhrubfoundation.org');
define('ADMIN_PASS', 'ChangeThisPassword!');

// (Optional) Timezone
date_default_timezone_set('Asia/Kolkata');
