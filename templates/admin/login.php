<?php
// If POST came directly to index.php (handled above), this file would have been included before output.
// For GET (normal render), just show the form.

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $email = $_POST['email'] ?? '';
    $pass  = $_POST['password'] ?? '';

    if ($email === ADMIN_USER && $pass === ADMIN_PASS) {
        $_SESSION['admin_logged_in'] = true;
        header('Location: ' . BASE_URL . '/index.php?page=admin/dashboard');
        exit;
    }
    // On invalid login, redirect back with message (or you could set a flag and render)
    header('Location: ' . BASE_URL . '/index.php?page=admin/login&error=1');
    exit;
}
?>
<section class="auth">
  <h1>Admin Login</h1>
  <?php if (!empty($_GET['error'])): ?>
    <p class="error">Invalid credentials. Please try again.</p>
  <?php endif; ?>
  <form method="post" action="<?= BASE_URL ?>/index.php?page=admin/login">
    <label>Email</label>
    <input type="email" name="email" required placeholder="admin@dhrubfoundation.org">
    <label>Password</label>
    <input type="password" name="password" required placeholder="Your password">
    <button type="submit" class="btn">Login</button>
  </form>
</section>
