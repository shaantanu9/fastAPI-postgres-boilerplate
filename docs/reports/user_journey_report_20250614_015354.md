# 🔐 User Journey Test Report

## 📊 Test Summary

| Metric | Value |
|--------|-------|
| **Total Tests** | 5 |
| **Passed** | 2 ✅ |
| **Failed** | 3 ❌ |
| **Success Rate** | 40.0% |
| **Test Date** | 2025-06-14 01:53:54 |
| **Test User** | testuser_nv5zj01y@example.com |

## 🔍 Detailed Results

### 1. ✅ Server Health Check - PASS

**Timestamp**: 2025-06-14T01:53:51.939383

**Details**:
- **Status Code**: 200
- **Message**: Server is running

**Response Data**:
```json
{
  "status": "healthy",
  "timestamp": 1749846231.93753
}
```

---

### 2. ❌ User Registration - FAIL

**Timestamp**: 2025-06-14T01:53:52.468973

**Details**:
- **Status Code**: 500
- **Email**: testuser_nv5zj01y@example.com
- **Username**: testuser_nv5zj01y
- **Message**: Registration failed: {"detail":"Internal server error during timeout handling","error_code":"TIMEOUT_MIDDLEWARE_ERROR","duration":0.01}

**Response Data**:
```json
{
  "detail": "Internal server error during timeout handling",
  "error_code": "TIMEOUT_MIDDLEWARE_ERROR",
  "duration": 0.01
}
```

---

### 3. ❌ User Login - FAIL

**Timestamp**: 2025-06-14T01:53:52.992904

**Details**:
- **Status Code**: 500
- **Email**: testuser_nv5zj01y@example.com
- **Has Access Token**: False
- **Has Refresh Token**: False
- **Message**: Login failed: {"detail":"Internal server error during timeout handling","error_code":"TIMEOUT_MIDDLEWARE_ERROR","duration":0.01}

---

### 4. ❌ Token Validation - FAIL

**Timestamp**: 2025-06-14T01:53:53.497661

**Details**:
- **Message**: No access token available

---

### 5. ✅ Password Reset - PASS

**Timestamp**: 2025-06-14T01:53:54.010475

**Details**:
- **Status Code**: 200
- **Email**: testuser_nv5zj01y@example.com
- **Message**: Password reset email sent

**Response Data**:
```json
{
  "message": "If the email exists, a password reset link has been sent"
}
```

---

🔧 **NEEDS WORK**: Significant issues found.

### ✅ Working Features
- Server Health Check
- Password Reset

### ❌ Issues Found
- **User Registration**: Registration failed: {"detail":"Internal server error during timeout handling","error_code":"TIMEOUT_MIDDLEWARE_ERROR","duration":0.01}
- **User Login**: Login failed: {"detail":"Internal server error during timeout handling","error_code":"TIMEOUT_MIDDLEWARE_ERROR","duration":0.01}
- **Token Validation**: No access token available
