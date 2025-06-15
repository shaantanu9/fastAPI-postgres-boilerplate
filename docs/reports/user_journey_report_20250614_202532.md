# 🔐 User Journey Test Report

## 📊 Test Summary

| Metric | Value |
|--------|-------|
| **Total Tests** | 5 |
| **Passed** | 2 ✅ |
| **Failed** | 3 ❌ |
| **Success Rate** | 40.0% |
| **Test Date** | 2025-06-14 20:25:32 |
| **Test User** | testuser_i725u41s@example.com |

## 🔍 Detailed Results

### 1. ✅ Server Health Check - PASS

**Timestamp**: 2025-06-14T20:25:30.281415

**Details**:
- **Status Code**: 200
- **Message**: Server is running

**Response Data**:
```json
{
  "status": "healthy",
  "timestamp": 1749912930.277872
}
```

---

### 2. ❌ User Registration - FAIL

**Timestamp**: 2025-06-14T20:25:30.802956

**Details**:
- **Status Code**: 400
- **Email**: testuser_i725u41s@example.com
- **Username**: testuser_i725u41s
- **Message**: Registration failed: {"detail":{"message":"Password does not meet security requirements","errors":["Password contains common patterns"],"strength":"Strong"}}

**Response Data**:
```json
{
  "detail": {
    "message": "Password does not meet security requirements",
    "errors": [
      "Password contains common patterns"
    ],
    "strength": "Strong"
  }
}
```

---

### 3. ❌ User Login - FAIL

**Timestamp**: 2025-06-14T20:25:31.318829

**Details**:
- **Status Code**: 422
- **Email**: testuser_i725u41s@example.com
- **Has Access Token**: False
- **Has Refresh Token**: False
- **Message**: Login failed: {"detail":[{"type":"model_attributes_type","loc":["body"],"msg":"Input should be a valid dictionary or object to extract fields from","input":"username=testuser_i725u41s%40example.com&password=TestPassword123%21"}]}

---

### 4. ❌ Token Validation - FAIL

**Timestamp**: 2025-06-14T20:25:31.823981

**Details**:
- **Message**: No access token available

---

### 5. ✅ Password Reset - PASS

**Timestamp**: 2025-06-14T20:25:32.409761

**Details**:
- **Status Code**: 200
- **Email**: testuser_i725u41s@example.com
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
- **User Registration**: Registration failed: {"detail":{"message":"Password does not meet security requirements","errors":["Password contains common patterns"],"strength":"Strong"}}
- **User Login**: Login failed: {"detail":[{"type":"model_attributes_type","loc":["body"],"msg":"Input should be a valid dictionary or object to extract fields from","input":"username=testuser_i725u41s%40example.com&password=TestPassword123%21"}]}
- **Token Validation**: No access token available
