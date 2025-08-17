<?php
require_once __DIR__ . '/config.php';
require_once __DIR__ . '/functions.php';

$page = $_GET['page'] ?? 'home';

/**
 * Special cases that must run BEFORE any output
 * (so they can set headers/redirect).
 */
if ($page === 'admin/logout') {
    require __DIR__ . '/templates/admin/logout.php';
    exit;
}
if ($page === 'admin/login' && $_SERVER['REQUEST_METHOD'] === 'POST') {
    // Handle login POST inside the template (no output yet)
    require __DIR__ . '/templates/admin/login.php';
    exit;
}

/** Map of allowed pages to template file paths */
$routes = [
    'home'      => __DIR__ . '/templates/home.php',
    'about'     => __DIR__ . '/templates/about.php',
    'programs'  => __DIR__ . '/templates/programs.php',
    'members'   => __DIR__ . '/templates/members.php',
    'gallery'   => __DIR__ . '/templates/gallery.php',
    'donate'    => __DIR__ . '/templates/donate.php',
    'contact'   => __DIR__ . '/templates/contact.php',

    // Admin pages
    'admin/login'     => __DIR__ . '/templates/admin/login.php',
    'admin/dashboard' => __DIR__ . '/templates/admin/dashboard.php',
    'admin/donations' => __DIR__ . '/templates/admin/donations.php',
];

$template = $routes[$page] ?? __DIR__ . '/templates/errors/404.php';

include __DIR__ . '/templates/partials/header.php';
include $template;
include __DIR__ . '/templates/partials/footer.php';
