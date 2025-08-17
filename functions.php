<?php

function e(string $s): string {
    return htmlspecialchars($s, ENT_QUOTES, 'UTF-8');
}

function isAdmin(): bool {
    return !empty($_SESSION['admin_logged_in']) && $_SESSION['admin_logged_in'] === true;
}

function requireAdmin(): void {
    if (!isAdmin()) {
        header('Location: ' . BASE_URL . '/index.php?page=admin/login');
        exit;
    }
}

function getMembers(): array {
    $path = __DIR__ . '/static/data/members.json';
    if (!file_exists($path)) return [];
    $json = file_get_contents($path);
    $data = json_decode($json, true);
    return is_array($data) ? $data : [];
}
