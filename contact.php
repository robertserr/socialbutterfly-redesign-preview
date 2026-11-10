<?php
/**
 * Contact form handler for socialbutterfly.agency
 * PHP 7.4 compatible. JSON for fetch(); redirect for no-JS POST.
 *
 * SPF for socialbutterfly.agency is Outlook-only (`v=spf1 include:spf.protection.outlook.com -all`),
 * so mail is sent From the SiteGround account address, with Reply-To set to the visitor.
 * CGI PHP mail() is unreliable here; messages are injected with /usr/sbin/sendmail.
 */
declare(strict_types=1);

// Recipient: Meghan's Microsoft 365 mailbox.
const MAIL_TO = 'meghan@socialbutterfly.agency';

const FROM_NAME = 'Social Butterfly Website';
const FROM_EMAIL = 'u1214-2rysfpfe4znk@gtxm1087.siteground.biz';
const ENVELOPE_FROM = 'u1214-2rysfpfe4znk@gtxm1087.siteground.biz';

const MIN_SECONDS = 3;
const MAX_SECONDS = 86400;
const RATE_LIMIT = 5;
const RATE_WINDOW = 3600;
const MAX_NAME = 120;
const MAX_EMAIL = 200;
const MAX_PHONE = 60;
const MAX_COMPANY = 160;
const MAX_SERVICE = 160;
const MAX_MESSAGE = 4000;

const ALLOWED_ORIGINS = array(
    'https://socialbutterfly.agency',
    'https://www.socialbutterfly.agency',
    'https://robertserr.github.io',
);

header('X-Content-Type-Options: nosniff');
header('Referrer-Policy: same-origin');
header('Cache-Control: no-store');

$origin = isset($_SERVER['HTTP_ORIGIN']) ? $_SERVER['HTTP_ORIGIN'] : '';
if (in_array($origin, ALLOWED_ORIGINS, true)) {
    header('Access-Control-Allow-Origin: ' . $origin);
    header('Vary: Origin');
    header('Access-Control-Allow-Methods: POST, OPTIONS');
    header('Access-Control-Allow-Headers: Accept, Content-Type, X-Requested-With');
}

if (($_SERVER['REQUEST_METHOD'] ?? '') === 'OPTIONS') {
    http_response_code(204);
    exit;
}

$want_json = wants_json();

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    if ($want_json) {
        respond_json(405, false, 'Please submit the contact form.');
    }
    header('Location: /#contact', true, 303);
    exit;
}

$first   = trim((string)($_POST['first'] ?? ''));
$last    = trim((string)($_POST['last'] ?? ''));
$email   = trim((string)($_POST['email'] ?? ''));
$phone   = trim((string)($_POST['phone'] ?? ''));
$company = trim((string)($_POST['company'] ?? ''));
$service = trim((string)($_POST['service'] ?? ''));
$message = trim((string)($_POST['message'] ?? ''));
$honeypot = (string)($_POST['website'] ?? '');
$form_t  = trim((string)($_POST['form_t'] ?? ''));

if ($honeypot !== '') {
    // Pretend success so bots don't retry.
    finish(true, 'Thank you — your message has been sent. We will be in touch soon.');
}

$errors = array();
if ($first === '' || mb_len($first) > MAX_NAME || has_header_chars($first)) {
    $errors[] = 'first';
}
if ($last === '' || mb_len($last) > MAX_NAME || has_header_chars($last)) {
    $errors[] = 'last';
}
if ($email === '' || !filter_var($email, FILTER_VALIDATE_EMAIL) || mb_len($email) > MAX_EMAIL || has_header_chars($email)) {
    $errors[] = 'email';
}
if ($phone !== '' && (mb_len($phone) > MAX_PHONE || has_header_chars($phone))) {
    $errors[] = 'phone';
}
if ($company !== '' && mb_len($company) > MAX_COMPANY) {
    $errors[] = 'company';
}
if ($service !== '' && (mb_len($service) > MAX_SERVICE || has_header_chars($service))) {
    $errors[] = 'service';
}
if (mb_len($message) > MAX_MESSAGE) {
    $errors[] = 'message';
}

if ($form_t !== '') {
    if (!preg_match('/^[0-9]{9,12}$/', $form_t)) {
        $errors[] = 'timing';
    } else {
        $elapsed = time() - (int)$form_t;
        if ($elapsed < MIN_SECONDS || $elapsed > MAX_SECONDS) {
            $errors[] = 'timing';
        }
    }
}

if ($errors) {
    finish(false, 'Please check the required fields and try again.', $errors);
}

if (!rate_ok()) {
    http_response_code(429);
    finish(false, 'Too many messages were sent just now. Please wait a little while and try again, or email us directly.');
}

$full_name = trim($first . ' ' . $last);
$subject = 'Website inquiry from ' . $full_name;
if ($service !== '') {
    $subject .= ' - ' . $service;
}
$subject = clean_header($subject);

$lines = array(
    'New website inquiry from the Social Butterfly contact form',
    '',
    'Name:    ' . $full_name,
    'Email:   ' . $email,
);
if ($phone !== '') {
    $lines[] = 'Phone:   ' . $phone;
}
if ($company !== '') {
    $lines[] = 'Company: ' . $company;
}
if ($service !== '') {
    $lines[] = 'Service: ' . $service;
}
$lines[] = '';
$lines[] = 'Message:';
$lines[] = ($message !== '' ? $message : '(No message included.)');
$lines[] = '';
$lines[] = '--';
$lines[] = 'Sent from https://socialbutterfly.agency/';
$body = implode("\n", $lines);

$from_header = encode_mailbox(FROM_NAME, FROM_EMAIL);
$reply_to = encode_mailbox($full_name, $email);

$headers = array(
    'To: ' . MAIL_TO,
    'From: ' . $from_header,
);
// Gmail silently drops mail when Reply-To equals To; keep Reply-To for real visitors.
if (strcasecmp($email, MAIL_TO) !== 0) {
    $headers[] = 'Reply-To: ' . $reply_to;
}
$headers[] = 'Subject: ' . encode_subject($subject);
$headers[] = 'MIME-Version: 1.0';
$headers[] = 'Content-Type: text/plain; charset=UTF-8';
$headers[] = 'Content-Transfer-Encoding: 8bit';
$headers[] = 'X-Mailer: Social Butterfly contact form';

// SiteGround's CGI PHP mail() returns true but the message never leaves the
// server. Injecting via /usr/sbin/sendmail (msmtp) does deliver.
$ok = send_via_sendmail($headers, $body, ENVELOPE_FROM);

if (!$ok) {
    finish(false, 'Sorry, the message could not be sent just now. Please email us directly at meghan@socialbutterfly.agency.');
}

finish(true, 'Thank you — your message has been sent. We will be in touch soon.');

function wants_json(): bool
{
    $accept = isset($_SERVER['HTTP_ACCEPT']) ? $_SERVER['HTTP_ACCEPT'] : '';
    $xrw = isset($_SERVER['HTTP_X_REQUESTED_WITH']) ? strtolower($_SERVER['HTTP_X_REQUESTED_WITH']) : '';
    return (strpos($accept, 'application/json') !== false) || $xrw === 'fetch' || $xrw === 'xmlhttprequest';
}

function finish(bool $ok, string $message, array $errors = array()): void
{
    if (wants_json()) {
        respond_json($ok ? 200 : 400, $ok, $message, $errors);
    }
    $loc = $ok ? '/?sent=1#contact' : '/?error=1#contact';
    header('Location: ' . $loc, true, 303);
    exit;
}

function respond_json(int $code, bool $ok, string $message, array $errors = array()): void
{
    http_response_code($code);
    header('Content-Type: application/json; charset=UTF-8');
    $payload = array('ok' => $ok, 'message' => $message);
    if ($errors) {
        $payload['errors'] = $errors;
    }
    echo json_encode($payload);
    exit;
}


function encode_subject(string $subject): string
{
    $clean = clean_header($subject);
    $clean = str_replace(array("\xE2\x80\x93", "\xE2\x80\x94", "\xE2\x80\x92"), '-', $clean);
    if (preg_match('/[^\x20-\x7E]/', $clean) && function_exists('mb_encode_mimeheader')) {
        $enc = mb_encode_mimeheader($clean, 'UTF-8', 'Q');
        return clean_header($enc);
    }
    return $clean;
}

function encode_mailbox(string $name, string $email): string
{
    $name = clean_header($name);
    $email = clean_header($email);
    if ($name === '') {
        return $email;
    }
    if (preg_match('/[^\x20-\x7E]/', $name) && function_exists('mb_encode_mimeheader')) {
        return mb_encode_mimeheader($name, 'UTF-8', 'Q') . ' <' . $email . '>';
    }
    if (preg_match('/[()<>@,;:\\\\".[\]]/', $name)) {
        $name = '"' . str_replace(array('\\', '"'), array('\\\\', '\\"'), $name) . '"';
    }
    return $name . ' <' . $email . '>';
}

function send_via_sendmail(array $headers, string $body, string $envelope_from): bool
{
    if ($envelope_from === '' || !filter_var($envelope_from, FILTER_VALIDATE_EMAIL)) {
        return false;
    }
    $raw = implode("\n", $headers) . "\n\n" . $body;
    if (substr($raw, -1) !== "\n") {
        $raw .= "\n";
    }
    $cmd = array('/usr/sbin/sendmail', '-t', '-i', '-f', $envelope_from);
    $desc = array(
        0 => array('pipe', 'r'),
        1 => array('pipe', 'w'),
        2 => array('pipe', 'w'),
    );
    $proc = proc_open($cmd, $desc, $pipes);
    if (!is_resource($proc)) {
        return false;
    }
    fwrite($pipes[0], $raw);
    fclose($pipes[0]);
    stream_get_contents($pipes[1]);
    stream_get_contents($pipes[2]);
    fclose($pipes[1]);
    fclose($pipes[2]);
    $status = proc_close($proc);
    return $status === 0;
}

function has_header_chars(string $value): bool
{
    return strpos($value, "\r") !== false || strpos($value, "\n") !== false;
}

function clean_header(string $value): string
{
    return str_replace(array("\r", "\n"), ' ', $value);
}

function mb_len(string $value): int
{
    return function_exists('mb_strlen') ? mb_strlen($value, 'UTF-8') : strlen($value);
}

function client_ip(): string
{
    $ip = isset($_SERVER['REMOTE_ADDR']) ? $_SERVER['REMOTE_ADDR'] : '0.0.0.0';
    return filter_var($ip, FILTER_VALIDATE_IP) ? $ip : '0.0.0.0';
}

function rate_dir(): string
{
    $outside = dirname(__DIR__) . '/form-rate';
    if (is_dir($outside) || @mkdir($outside, 0700, true)) {
        return $outside;
    }
    $tmp = rtrim(sys_get_temp_dir(), '/') . '/sb-form-rate';
    if (!is_dir($tmp)) {
        @mkdir($tmp, 0700, true);
    }
    return $tmp;
}

function rate_ok(): bool
{
    $dir = rate_dir();
    if (!is_dir($dir) || !is_writable($dir)) {
        return true;
    }
    $file = $dir . '/' . hash('sha256', client_ip()) . '.json';
    $now = time();
    $times = array();
    if (is_file($file)) {
        $raw = @file_get_contents($file);
        $decoded = $raw ? json_decode($raw, true) : null;
        if (is_array($decoded)) {
            $times = $decoded;
        }
    }
    $times = array_values(array_filter($times, function ($t) use ($now) {
        return is_int($t) && ($now - $t) < RATE_WINDOW;
    }));
    if (count($times) >= RATE_LIMIT) {
        return false;
    }
    $times[] = $now;
    @file_put_contents($file, json_encode($times), LOCK_EX);
    return true;
}
