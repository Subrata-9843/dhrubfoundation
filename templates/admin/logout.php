<?php
// No output before headers!
if (session_status() === PHP_SESSION_NONE) { session_start(); }
$_SESSION = [];
session_unset();
session_destroy();

header('Location: ' . (defined('BASE_URL') ? BASE_URL : '.') . '/index.php?page=admin/login');
exit;
