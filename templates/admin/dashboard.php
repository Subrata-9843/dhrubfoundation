<?php requireAdmin(); ?>
<section>
  <h1>Admin Dashboard</h1>
  <p>Welcome, you are logged in.</p>
  <div class="admin-links">
    <a class="btn" href="<?= BASE_URL ?>/?page=admin/donations">View Donations</a>
    <a class="btn-outline" href="<?= BASE_URL ?>/?page=admin/logout">Logout</a>
  </div>
</section>
