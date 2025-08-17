<?php /* Basic, clean header */ ?>
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Dhrub Foundation</title>
  <link rel="icon" href="<?= BASE_URL ?>/static/images/logo.png">
  <link rel="stylesheet" href="<?= BASE_URL ?>/static/css/custom.css">
  <script src="<?= BASE_URL ?>/static/js/main.js" defer></script>
</head>
<body>
<header class="site-header">
  <div class="container header-inner">
    <a class="brand" href="<?= BASE_URL ?>">
      <img src="<?= BASE_URL ?>/static/images/logo.png" alt="Logo" class="logo">
      <span>Dhrub Foundation</span>
    </a>
    <nav class="nav">
      <a href="<?= BASE_URL ?>/?page=home">Home</a>
      <a href="<?= BASE_URL ?>/?page=about">About</a>
      <a href="<?= BASE_URL ?>/?page=programs">Programs</a>
      <a href="<?= BASE_URL ?>/?page=members">Members</a>
      <a href="<?= BASE_URL ?>/?page=gallery">Gallery</a>
      <a href="<?= BASE_URL ?>/?page=donate">Donate</a>
      <a href="<?= BASE_URL ?>/?page=contact">Contact</a>
      <?php if (isAdmin()): ?>
        <a href="<?= BASE_URL ?>/?page=admin/dashboard">Admin</a>
        <a href="<?= BASE_URL ?>/?page=admin/logout">Logout</a>
      <?php else: ?>
        <a href="<?= BASE_URL ?>/?page=admin/login">Login</a>
      <?php endif; ?>
    </nav>
  </div>
</header>
<main class="container content">
