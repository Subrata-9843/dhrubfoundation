<?php $members = getMembers(); ?>
<section>
  <h1>Our Members</h1>
  <?php if (empty($members)): ?>
    <p>No members listed yet.</p>
  <?php else: ?>
    <div class="cards">
      <?php foreach ($members as $m): ?>
        <div class="card">
          <img src="<?= BASE_URL ?>/static/images/members/default.jpg" alt="<?= e($m['name']) ?>">
          <h3><?= e($m['name']) ?></h3>
          <p><?= e($m['role'] ?? 'Member') ?></p>
        </div>
      <?php endforeach; ?>
    </div>
  <?php endif; ?>
</section>
