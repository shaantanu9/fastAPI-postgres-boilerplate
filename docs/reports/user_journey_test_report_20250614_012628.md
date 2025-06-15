# User Journey Test Report

## 📊 Test Summary

- **Total Tests**: 9
- **Passed**: 3 ✅
- **Failed**: 6 ❌
- **Success Rate**: 33.3%
- **Test Date**: 2025-06-14 01:26:28
- **Test User**: test_6ngp3pa8@example.com

## 🔍 Detailed Results

### ✅ Server Health Check - PASS

**Timestamp**: 2025-06-14T01:26:23.690676

**Details**:
- **Status Code**: 200
- **Message**: Server is running and responsive

**Response Data**:
```json
{
  "status": "healthy",
  "timestamp": 1749844583.6883461
}
```

---

### ✅ API Documentation Access - PASS

**Timestamp**: 2025-06-14T01:26:24.202109

**Details**:
- **Status Code**: 200
- **Message**: API docs accessible

---

### ❌ User Registration - FAIL

**Timestamp**: 2025-06-14T01:26:24.734825

**Details**:
- **Status Code**: 500
- **Email**: test_6ngp3pa8@example.com
- **Username**: testuser_ap008e
- **Message**: Registration failed with status 500

**Response Data**:
```json
{
  "detail": "Internal server error during timeout handling",
  "error_code": "TIMEOUT_MIDDLEWARE_ERROR",
  "duration": 0.02
}
```

---

### ❌ User Login - FAIL

**Timestamp**: 2025-06-14T01:26:25.277213

**Details**:
- **Status Code**: 500
- **Email**: test_6ngp3pa8@example.com
- **Has Access Token**: False
- **Has Refresh Token**: False
- **Message**: Login failed with status 500

**Response Data**:
```json
{
  "detail": "Internal server error during timeout handling",
  "error_code": "TIMEOUT_MIDDLEWARE_ERROR",
  "duration": 0.01
}
```

---

### ❌ Token Validation - FAIL

**Timestamp**: 2025-06-14T01:26:25.780725

**Details**:
- **Message**: No access token available for validation

---

### ❌ Protected Routes Access - FAIL

**Timestamp**: 2025-06-14T01:26:26.285832

**Details**:
- **Message**: No access token available

---

### ❌ Token Refresh - FAIL

**Timestamp**: 2025-06-14T01:26:26.788234

**Details**:
- **Message**: No refresh token available

---

### ✅ Password Reset Flow - PASS

**Timestamp**: 2025-06-14T01:26:27.356034

**Details**:
- **Status Code**: 200
- **Email**: test_6ngp3pa8@example.com
- **Message**: Password reset email sent

**Response Data**:
```json
{
  "message": "If the email exists, a password reset link has been sent"
}
```

---

### ❌ User Logout - FAIL

**Timestamp**: 2025-06-14T01:26:27.861125

**Details**:
- **Message**: No access token available for logout

---

## 🎯 Recommendations

### ✅ Working Features
- Server Health Check
- API Documentation Access
- Password Reset Flow

### ⚠️ Issues Found
- **User Registration**: Registration failed with status 500
- **User Login**: Login failed with status 500
- **Token Validation**: No access token available for validation
- **Protected Routes Access**: No access token available
- **Token Refresh**: No refresh token available
- **User Logout**: No access token available for logout

### 🚀 Overall Assessment

The user journey test completed with a **33.3% success rate**. 

🚨 **CRITICAL**: Major issues found that need immediate attention.