# 🧪 Manual Testing Guide - Umukozi Authentication

## 📋 Test Accounts Ready

The following test accounts have been created and are ready for manual testing:

### 🔧 **Worker Account**
- **Email:** `testworker@umukozi.rw`
- **Password:** `testpassword123`
- **Name:** Test Worker
- **Phone:** +250788123456

### 👤 **Employer Account**
- **Email:** `testemployer@umukozi.rw`
- **Password:** `testpassword123`
- **Name:** Test Employer
- **Phone:** +250787654321

---

## 🌐 How to Test

### **Step 1: Access the Application**
1. Open your web browser
2. Go to: `http://127.0.0.1:5000`
3. You should see the Umukozi homepage

### **Step 2: Test Worker Login**
1. Click "Login" in the top navigation
2. Enter worker credentials:
   - Email: `testworker@umukozi.rw`
   - Password: `testpassword123`
3. Click "Login"
4. **Expected:** You should be redirected to the Worker Dashboard

### **Step 3: Test Worker Dashboard**
1. Verify you see the Worker Dashboard
2. Check for:
   - Welcome message with worker name
   - Profile completion status
   - Recent applications section
   - Quick actions menu
   - Recommended jobs section
3. **Expected:** All sections should be visible and properly formatted

### **Step 4: Test Employer Login**
1. Click "Logout" (top navigation)
2. Click "Login" again
3. Enter employer credentials:
   - Email: `testemployer@umukozi.rw`
   - Password: `testpassword123`
4. Click "Login"
5. **Expected:** You should be redirected to the Employer Dashboard

### **Step 5: Test Employer Dashboard**
1. Verify you see the Employer Dashboard
2. Check for:
   - Welcome message with employer name
   - Statistics overview
   - Recent job posts section
   - Recent activity feed
   - Recommended workers section
3. **Expected:** All sections should be visible and properly formatted

### **Step 6: Test New User Registration**
1. Click "Logout"
2. Click "Sign Up"
3. Test the registration form:
   - **Role Selection:** Choose from dropdown (Worker/Employer)
   - **Full Name:** Enter any name
   - **Email:** Use a unique email (e.g., `newuser@test.com`)
   - **Phone:** Enter phone number
   - **Password:** Create a password
   - **Confirm Password:** Re-enter password
   - **Terms:** Check the agreement box
4. Click "Create Account"
5. **Expected:** Success message and redirect to login

### **Step 7: Test Form Validation**
1. Try to register with:
   - Empty required fields
   - Invalid email format
   - Passwords that don't match
   - Already registered email
2. **Expected:** Appropriate error messages for each case

### **Step 8: Test Mobile Responsiveness**
1. Resize your browser window to mobile size
2. Test navigation, forms, and dashboards
3. **Expected:** Everything should be readable and usable on small screens

---

## ✅ Success Indicators

### **Login Should Work If:**
- ✅ Credentials are accepted
- ✅ Redirected to correct dashboard (Worker vs Employer)
- ✅ User name appears in welcome message
- ✅ Dashboard content loads properly

### **Registration Should Work If:**
- ✅ New account is created successfully
- ✅ Success message appears
- ✅ Redirected to login page
- ✅ Can login with new credentials

### **Form Validation Should Work If:**
- ✅ Required fields are enforced
- ✅ Email format is validated
- ✅ Password confirmation works
- ✅ Duplicate emails are rejected

---

## 🐛 Common Issues & Solutions

### **Issue: Login Fails**
- **Solution:** Check email/password spelling, ensure account exists

### **Issue: Registration Fails**
- **Solution:** Use unique email, fill all required fields, accept terms

### **Issue: Dashboard Looks Empty**
- **Solution:** This is normal for new accounts, sample data will appear

### **Issue: Mobile Layout Broken**
- **Solution:** Refresh page, check browser zoom level

---

## 📊 Test Results Summary

### **Automated Tests Results:**
- ✅ Database Connection: **PASS**
- ✅ Worker Registration: **PASS**
- ✅ Employer Registration: **PASS**
- ✅ Password Authentication: **PASS**
- ✅ Database Relationships: **PASS**
- ✅ Duplicate Email Detection: **PASS**
- ⚠️ Form Validation: **PARTIAL** (works at DB level)

### **Ready for Manual Testing:**
- ✅ Test accounts created
- ✅ Application running on http://127.0.0.1:5000
- ✅ All authentication endpoints functional
- ✅ Database populated with test data

---

## 🎯 Next Steps After Testing

1. **If all tests pass:** Authentication system is production-ready
2. **If issues found:** Note the specific problems for debugging
3. **After testing:** Proceed to test additional features (job posting, messaging, etc.)

---

## 📞 Support

If you encounter any issues during testing:
1. Check the browser console for JavaScript errors
2. Verify the Flask server is still running
3. Check the terminal for any error messages
4. Review the test output above for known issues

**Happy Testing! 🚀**
