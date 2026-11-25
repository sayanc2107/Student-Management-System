// ==============================================================================
// STUDENT MANAGEMENT WEB APP - CLIENT-SIDE CONTROLLER
// ==============================================================================

let currentUser = null;
let currentTab = 'dashboard';
let cachedStudents = [];
let cachedFees = [];
let activeRosterClassId = null;
let classSelectedYear = new Date().getFullYear();
let classSelectedMonth = new Date().getMonth() + 1;
let activeFeedbackClassId = null;

// Debounce utility
function debounce(func, wait) {
  let timeout;
  return function (...args) {
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(this, args), wait);
  };
}

// Format currency
function formatINR(amount) {
  return '₹' + Number(amount || 0).toLocaleString('en-IN', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2
  });
}

// Format date nicely
function formatDate(dateStr) {
  if (!dateStr) return '';
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric'
    });
  } catch (e) {
    return dateStr;
  }
}

// API Helper
async function apiCall(endpoint, method = 'GET', data = null) {
  const token = localStorage.getItem('sms_auth_token');
  const headers = {
    'Content-Type': 'application/json'
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const options = { method, headers };
  if (data && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
    options.body = JSON.stringify(data);
  }

  const res = await fetch(endpoint, options);
  if (res.status === 401) {
    // Session expired or unauthenticated
    localStorage.removeItem('sms_auth_token');
    showAuthScreen();
    throw new Error('Session expired. Please sign in again.');
  }

  const json = await res.json();
  if (!res.ok) {
    throw new Error(json.detail || 'API request failed');
  }
  return json;
}

// ==============================================================================
// AUTHENTICATION
// ==============================================================================

async function checkAuth() {
  const token = localStorage.getItem('sms_auth_token');
  if (!token) {
    showAuthScreen();
    return;
  }

  try {
    currentUser = await apiCall('/api/auth/me');
    showMainApp();
  } catch (err) {
    console.error('Auth verification failed:', err);
    showAuthScreen();
  }
}

function showAuthScreen() {
  document.getElementById('auth-screen').classList.remove('hidden');
  document.getElementById('main-app').classList.add('hidden');
  currentUser = null;
  lucide.createIcons();
}

function showMainApp() {
  document.getElementById('auth-screen').classList.add('hidden');
  document.getElementById('main-app').classList.remove('hidden');

  // Render navigation according to role
  renderNavigation();
  updateUserProfileDisplay();

  // Load default view
  navigateTo(currentUser.role === 'teacher' ? 'dashboard' : 'student-dashboard');
}

async function handleLogin(e) {
  e.preventDefault();
  const idValue = document.getElementById('login-email').value.trim();
  const password = document.getElementById('login-password').value;
  const btn = document.getElementById('login-btn');
  const errorBox = document.getElementById('auth-error');

  btn.disabled = true;
  btn.innerHTML = '<span>Verifying...</span>';
  errorBox.classList.add('hidden');

  try {
    const res = await apiCall('/api/auth/login', 'POST', {
      email: idValue,
      username: idValue,
      password: password
    });
    localStorage.setItem('sms_auth_token', res.access_token);
    currentUser = res.user;
    showMainApp();
  } catch (err) {
    errorBox.classList.remove('hidden');
    document.getElementById('auth-error-msg').innerText = err.message;
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span>Sign In</span><i data-lucide="arrow-right" class="w-4 h-4"></i>';
    lucide.createIcons();
  }
}

async function quickLogin(emailOrUsername, password) {
  document.getElementById('login-email').value = emailOrUsername;
  document.getElementById('login-password').value = password;
  const fakeEvent = { preventDefault: () => { } };
  await handleLogin(fakeEvent);
}

function logout() {
  localStorage.removeItem('sms_auth_token');
  showAuthScreen();
}

function updateUserProfileDisplay() {
  if (!currentUser) return;
  document.getElementById('user-display-name').innerText = currentUser.name || 'User';
  const unameDisplay = currentUser.username ? `@${currentUser.username}` : '';
  const emailDisplay = currentUser.email || '';
  document.getElementById('user-display-email').innerText = unameDisplay ? `${unameDisplay} • ${emailDisplay}` : emailDisplay;

  const roleBadge = document.getElementById('role-badge');
  roleBadge.innerText = currentUser.role === 'teacher' ? 'Teacher' : 'Student';
  roleBadge.className = currentUser.role === 'teacher'
    ? 'px-1.5 py-0.2 rounded font-semibold text-[10px] uppercase bg-brand-500/20 text-brand-300'
    : 'px-1.5 py-0.2 rounded font-semibold text-[10px] uppercase bg-emerald-500/20 text-emerald-300';

  const initials = (currentUser.name || 'User').split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
  document.getElementById('user-avatar').innerText = initials;
}

// ==============================================================================
// NAVIGATION & VIEWS
// ==============================================================================

function renderNavigation() {
  const nav = document.getElementById('nav-links');
  if (!currentUser) return;

  if (currentUser.role === 'teacher') {
    nav.innerHTML = `
      <button onclick="navigateTo('dashboard')" data-nav="dashboard" class="nav-item w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 transition">
        <i data-lucide="layout-dashboard" class="w-4 h-4"></i>
        <span>Dashboard</span>
      </button>
      <button onclick="navigateTo('students')" data-nav="students" class="nav-item w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 transition">
        <i data-lucide="users" class="w-4 h-4"></i>
        <span>Students</span>
      </button>
      <button onclick="navigateTo('classes')" data-nav="classes" class="nav-item w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 transition">
        <i data-lucide="calendar" class="w-4 h-4"></i>
        <span>Schedule & Attendance</span>
      </button>
      <button onclick="navigateTo('homework')" data-nav="homework" class="nav-item w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 transition">
        <i data-lucide="book-open" class="w-4 h-4"></i>
        <span>Homework & Reviews</span>
      </button>
      <button onclick="navigateTo('exams')" data-nav="exams" class="nav-item w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 transition">
        <i data-lucide="award" class="w-4 h-4"></i>
        <span>Exams & Tests</span>
      </button>
      <button onclick="navigateTo('fees')" data-nav="fees" class="nav-item w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 transition">
        <i data-lucide="indian-rupee" class="w-4 h-4"></i>
        <span>Fees & Payments</span>
      </button>
      <button onclick="navigateTo('settings')" data-nav="settings" class="nav-item w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 transition">
        <i data-lucide="settings" class="w-4 h-4"></i>
        <span>Settings & UPI</span>
      </button>
    `;
  } else {
    // Student navigation
    nav.innerHTML = `
      <button onclick="navigateTo('student-dashboard')" data-nav="student-dashboard" class="nav-item w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 transition">
        <i data-lucide="home" class="w-4 h-4"></i>
        <span>My Dashboard</span>
      </button>
      <button onclick="navigateTo('classes')" data-nav="classes" class="nav-item w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 transition">
        <i data-lucide="calendar" class="w-4 h-4"></i>
        <span>My Schedule</span>
      </button>
      <button onclick="navigateTo('homework')" data-nav="homework" class="nav-item w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 transition">
        <i data-lucide="file-text" class="w-4 h-4"></i>
        <span>My Homework</span>
      </button>
      <button onclick="navigateTo('exams')" data-nav="exams" class="nav-item w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 transition">
        <i data-lucide="award" class="w-4 h-4"></i>
        <span>My Exams</span>
      </button>
      <button onclick="navigateTo('fees')" data-nav="fees" class="nav-item w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 transition">
        <i data-lucide="qr-code" class="w-4 h-4"></i>
        <span>Fees & Direct UPI</span>
      </button>
    `;
  }
  lucide.createIcons();
}

function navigateTo(tabId) {
  currentTab = tabId;

  // Hide all view containers
  const views = [
    'view-teacher-dashboard',
    'view-student-dashboard',
    'view-students',
    'view-classes',
    'view-homework',
    'view-exams',
    'view-fees',
    'view-settings'
  ];
  views.forEach(v => document.getElementById(v).classList.add('hidden'));

  // Update nav link styles
  document.querySelectorAll('.nav-item').forEach(el => {
    if (el.getAttribute('data-nav') === tabId) {
      el.classList.add('bg-brand-600', 'text-white', 'shadow-sm');
      el.classList.remove('text-slate-300');
    } else {
      el.classList.remove('bg-brand-600', 'text-white', 'shadow-sm');
      el.classList.add('text-slate-300');
    }
  });

  // Set page headers
  const pageTitle = document.getElementById('page-title');
  const pageSub = document.getElementById('page-subtitle');
  const headerActions = document.getElementById('header-action-container');
  if (headerActions) {
    let actionsHtml = '';
    if (currentUser && currentUser.role === 'teacher') {
      actionsHtml += `
        <button onclick="preparePaymentModal()" title="Record Received Payment" class="px-3 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs flex items-center gap-1.5 shadow-sm transition">
          <i data-lucide="plus-circle" class="w-3.5 h-3.5"></i>
          <span class="hidden sm:inline">Record Payment</span>
        </button>
      `;
    }
    actionsHtml += `
      <button onclick="refreshCurrentView()" title="Refresh Current Menu" class="px-3 py-1.5 rounded-xl border border-slate-200 hover:bg-slate-100 text-slate-700 font-semibold text-xs flex items-center gap-1.5 transition shadow-sm bg-white">
        <i data-lucide="refresh-cw" class="w-3.5 h-3.5 text-brand-600" id="global-refresh-icon"></i>
        <span class="hidden sm:inline">Refresh</span>
      </button>
    `;
    headerActions.innerHTML = actionsHtml;
  }

  switch (tabId) {
    case 'dashboard':
      pageTitle.innerText = 'Teacher Dashboard';
      pageSub.innerText = 'Real-time overview of classes, homework due, pending reviews, and fees';
      document.getElementById('view-teacher-dashboard').classList.remove('hidden');
      loadTeacherDashboard();
      break;

    case 'student-dashboard':
      pageTitle.innerText = 'Student Portal';
      pageSub.innerText = 'Your upcoming classes, homework assignments, and academic status';
      document.getElementById('view-student-dashboard').classList.remove('hidden');
      loadStudentDashboard();
      break;

    case 'students':
      pageTitle.innerText = 'Student Management';
      pageSub.innerText = 'Manage enrolled students, profiles, guardian contacts, and notes';
      document.getElementById('view-students').classList.remove('hidden');
      loadStudents();
      break;

    case 'classes':
      pageTitle.innerText = currentUser.role === 'teacher' ? 'Class Schedule & Attendance' : 'My Scheduled Classes';
      pageSub.innerText = 'Class timings, live session links, and attendance tracking';
      document.getElementById('view-classes').classList.remove('hidden');
      loadClasses();
      break;

    case 'homework':
      pageTitle.innerText = currentUser.role === 'teacher' ? 'Homework & Submissions Review' : 'My Homework Assignments';
      pageSub.innerText = 'Instructions, due dates, student submission files, and teacher feedback';
      document.getElementById('view-homework').classList.remove('hidden');
      loadHomework();
      break;

    case 'exams':
      pageTitle.innerText = 'Exams & Assessments';
      pageSub.innerText = 'Exam syllabus, schedules, and Google Form examination links';
      document.getElementById('view-exams').classList.remove('hidden');
      loadExams();
      break;

    case 'fees':
      pageTitle.innerText = currentUser.role === 'teacher' ? 'Fees Ledger & Manual Payments' : 'Fee Ledger & Direct UPI Payment';
      pageSub.innerText = 'Direct UPI payments, fee dues, payment history, and reversal adjustments';
      document.getElementById('view-fees').classList.remove('hidden');
      loadFees();
      break;

    case 'settings':
      pageTitle.innerText = 'Settings & Tuition Profile';
      pageSub.innerText = 'Tuition details, teacher contact, UPI ID, and MongoDB connection status';
      document.getElementById('view-settings').classList.remove('hidden');
      loadSettings();
      break;
  }

  // Adjust UI elements visibility based on role
  adjustRoleVisibility();
  lucide.createIcons();

  // Close mobile sidebar if open
  document.getElementById('sidebar').classList.remove('block');
  document.getElementById('sidebar').classList.add('hidden', 'md:flex');
}

function refreshCurrentView() {
  const icon = document.getElementById('global-refresh-icon');
  if (icon) icon.classList.add('animate-spin');

  switch (currentTab) {
    case 'dashboard':
      loadTeacherDashboard();
      break;
    case 'student-dashboard':
      loadStudentDashboard();
      break;
    case 'students':
      loadStudents();
      break;
    case 'classes':
      loadClasses();
      break;
    case 'homework':
      loadHomework();
      break;
    case 'exams':
      loadExams();
      break;
    case 'fees':
      loadFees();
      break;
    case 'settings':
      loadSettings();
      break;
    default:
      if (currentUser && currentUser.role === 'teacher') loadTeacherDashboard();
      else loadStudentDashboard();
  }

  setTimeout(() => {
    if (icon) icon.classList.remove('animate-spin');
    lucide.createIcons();
  }, 500);
}

function toggleMobileMenu() {
  const sidebar = document.getElementById('sidebar');
  if (sidebar.classList.contains('hidden')) {
    sidebar.classList.remove('hidden');
    sidebar.classList.add('block');
  } else {
    sidebar.classList.add('hidden');
    sidebar.classList.remove('block');
  }
}

function adjustRoleVisibility() {
  const isTeacher = currentUser && currentUser.role === 'teacher';

  // Hide teacher only action buttons when student
  const teacherOnlyElements = [
    'class-teacher-actions',
    'hw-teacher-actions',
    'exam-teacher-actions',
    'fee-teacher-actions',
    'fee-th-actions',
    'payment-th-actions'
  ];
  teacherOnlyElements.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      if (isTeacher) el.classList.remove('hidden');
      else el.classList.add('hidden');
    }
  });

  // Student UPI Card on fees view
  const studentUpiCard = document.getElementById('student-upi-payment-card');
  if (studentUpiCard) {
    if (!isTeacher) studentUpiCard.classList.remove('hidden');
    else studentUpiCard.classList.add('hidden');
  }
}

// ==============================================================================
// TEACHER DASHBOARD
// ==============================================================================

async function loadTeacherDashboard() {
  try {
    const data = await apiCall('/api/dashboard/teacher');

    // KPI Counters
    document.getElementById('stat-active-students').innerText = data.stats.activeStudents || 0;
    document.getElementById('stat-upcoming-classes').innerText = data.stats.upcomingClasses || 0;
    document.getElementById('stat-pending-reviews').innerText = data.stats.pendingReviews || 0;
    document.getElementById('stat-pending-fees').innerText = formatINR(data.stats.totalPendingFees || 0);

    // Upcoming Classes List
    const classesContainer = document.getElementById('dash-upcoming-classes');
    if (!data.upcomingClasses || data.upcomingClasses.length === 0) {
      classesContainer.innerHTML = '<div class="text-center py-6 text-slate-400 text-xs">No classes scheduled in the next 7 days.</div>';
    } else {
      classesContainer.innerHTML = data.upcomingClasses.map(c => {
        const isOnline = c.mode !== 'Offline';
        return `
        <div class="p-3 rounded-xl border border-slate-100 bg-slate-50 hover:bg-slate-100/80 transition flex items-center justify-between gap-3 text-xs">
          <div class="min-w-0">
            <div class="flex items-center gap-2">
              <span class="px-2 py-0.5 rounded font-bold text-[10px] bg-brand-100 text-brand-700">${c.subject}</span>
              <span class="font-bold text-slate-900 truncate">${c.title}</span>
              <span class="px-1.5 py-0.2 rounded text-[10px] font-semibold ${isOnline ? 'bg-blue-100 text-blue-700' : 'bg-amber-100 text-amber-800'}">${isOnline ? '🌐 Online' : '📍 Offline'}</span>
            </div>
            <div class="text-slate-500 mt-1 flex items-center gap-2 text-[11px]">
              <span>📅 ${formatDate(c.date)}</span>
              <span>⏰ ${c.startTime} - ${c.endTime}</span>
              ${c.grade ? `<span>• ${c.grade}</span>` : ''}
            </div>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            ${isOnline && c.meetingLink ? `<a href="${c.meetingLink}" target="_blank" class="px-2.5 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-[11px] flex items-center gap-1"><i data-lucide="video" class="w-3 h-3"></i> Meet</a>` : ''}
            <button onclick="openClassFeedbackModal('${c.id}', '${(c.title || '').replace(/'/g, "\\'")}', '${c.date}', '${c.mode || 'Online'}')" class="px-2 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium text-[11px]">Remarks</button>
            <button onclick="openAttendanceModal('${c.id}', '${c.title}')" class="px-2.5 py-1 rounded-lg bg-slate-200 hover:bg-slate-300 text-slate-700 font-medium text-[11px]">Roster</button>
          </div>
        </div>
      `;
      }).join('');
    }

    // Pending Reviews
    const reviewsContainer = document.getElementById('dash-pending-submissions');
    if (!data.pendingSubmissions || data.pendingSubmissions.length === 0) {
      reviewsContainer.innerHTML = '<div class="text-center py-6 text-slate-400 text-xs">All submitted homework has been reviewed! 🎉</div>';
    } else {
      reviewsContainer.innerHTML = data.pendingSubmissions.map(s => `
        <div class="p-3 rounded-xl border border-amber-200/60 bg-amber-50/40 flex items-center justify-between gap-3 text-xs">
          <div class="min-w-0">
            <p class="font-bold text-slate-900">${s.studentName}</p>
            <p class="text-slate-500 text-[11px] truncate">${s.homeworkTitle} &bull; <span class="text-amber-700 font-semibold">${s.subject}</span></p>
          </div>
          <button onclick="openSubmissionsModal('${s.homeworkId}', '${s.homeworkTitle}')" class="px-3 py-1 rounded-lg bg-amber-500 hover:bg-amber-600 text-white font-semibold text-[11px] shrink-0">
            Grade & Feedback
          </button>
        </div>
      `).join('');
    }

    // Homework Deadlines & Overdue
    const deadlinesContainer = document.getElementById('dash-homework-deadlines');
    let hwHtml = '';
    if (data.homeworkOverdue && data.homeworkOverdue.length > 0) {
      hwHtml += data.homeworkOverdue.map(h => `
        <div class="p-2.5 rounded-xl border border-rose-200 bg-rose-50/60 flex items-center justify-between text-xs">
          <div>
            <span class="px-1.5 py-0.2 rounded text-[10px] font-bold bg-rose-200 text-rose-800 uppercase">OVERDUE</span>
            <span class="font-bold text-slate-900 ml-1.5">${h.title}</span>
            <p class="text-[11px] text-slate-500 mt-0.5">Due: ${formatDate(h.dueDate)} &bull; ${h.subject}</p>
          </div>
          <span class="text-xs text-rose-700 font-bold">${h.pendingReviewCount || 0} awaiting review</span>
        </div>
      `).join('');
    }
    if (data.homeworkDueSoon && data.homeworkDueSoon.length > 0) {
      hwHtml += data.homeworkDueSoon.map(h => `
        <div class="p-2.5 rounded-xl border border-indigo-100 bg-indigo-50/40 flex items-center justify-between text-xs">
          <div>
            <span class="px-1.5 py-0.2 rounded text-[10px] font-bold bg-indigo-200 text-indigo-800 uppercase">DUE SOON</span>
            <span class="font-bold text-slate-900 ml-1.5">${h.title}</span>
            <p class="text-[11px] text-slate-500 mt-0.5">Due: ${formatDate(h.dueDate)} &bull; ${h.subject}</p>
          </div>
          <span class="text-xs text-indigo-700 font-bold">${h.submissionCount || 0} submitted</span>
        </div>
      `).join('');
    }
    if (!hwHtml) {
      hwHtml = '<div class="text-center py-6 text-slate-400 text-xs">No pending homework deadlines right now.</div>';
    }
    deadlinesContainer.innerHTML = hwHtml;

    // Students with unpaid fees
    const unpaidContainer = document.getElementById('dash-unpaid-students');
    if (!data.unpaidStudents || data.unpaidStudents.length === 0) {
      unpaidContainer.innerHTML = '<div class="text-center py-6 text-emerald-600 font-medium text-xs">All student tuition fees are fully settled! 👍</div>';
    } else {
      unpaidContainer.innerHTML = data.unpaidStudents.map(u => `
        <div class="p-3 rounded-xl border border-slate-100 bg-slate-50 flex items-center justify-between text-xs">
          <div>
            <p class="font-bold text-slate-900">${u.studentName}</p>
            <p class="text-[11px] text-slate-400">${u.grade || 'Tuition'} &bull; Total Billed: ${formatINR(u.totalFees)}</p>
          </div>
          <div class="text-right">
            <span class="font-bold text-rose-600 text-sm">${formatINR(u.balance)} Due</span>
            <div>
              <button onclick="openPaymentForStudent('${u.studentId}', ${u.balance})" class="text-[11px] text-brand-600 hover:text-brand-700 font-semibold underline">
                Record Payment
              </button>
            </div>
          </div>
        </div>
      `).join('');
    }

    lucide.createIcons();
  } catch (err) {
    console.error('Failed to load teacher dashboard:', err);
  }
}

// ==============================================================================
// STUDENT DASHBOARD
// ==============================================================================

async function loadStudentDashboard() {
  try {
    const data = await apiCall('/api/dashboard/student');
    if (data.error) {
      alert(data.error);
      return;
    }

    document.getElementById('student-welcome-name').innerText = currentUser.name || 'Student';
    document.getElementById('student-stat-classes').innerText = data.stats.upcomingClasses || 0;
    document.getElementById('student-stat-homework').innerText = data.stats.pendingHomework || 0;
    document.getElementById('student-stat-balance').innerText = formatINR(data.stats.balanceDue || 0);

    // Teacher card
    if (data.teacherContact) {
      document.getElementById('teacher-card-name').innerText = data.teacherContact.name;
      const emailLink = document.getElementById('teacher-card-email-link');
      emailLink.innerText = data.teacherContact.email;
      emailLink.href = `mailto:${data.teacherContact.email}?subject=Student%20Inquiry%20from%20${encodeURIComponent(currentUser.name)}`;

      const mailtoBtn = document.getElementById('student-mailto-btn');
      if (mailtoBtn) {
        mailtoBtn.href = `mailto:${data.teacherContact.email}?subject=Message%20from%20${encodeURIComponent(currentUser.name)}`;
      }

      document.getElementById('teacher-card-phone').innerText = data.teacherContact.phone || '+91 98765 43210';
      document.getElementById('teacher-card-upi').innerText = data.teacherContact.upiId || 'teacher@upi';
    }

    // Classes
    const classesContainer = document.getElementById('student-dash-classes');
    if (!data.upcomingClasses || data.upcomingClasses.length === 0) {
      classesContainer.innerHTML = '<div class="text-center py-6 text-slate-400 text-xs">No upcoming classes scheduled.</div>';
    } else {
      classesContainer.innerHTML = data.upcomingClasses.map(c => {
        const isOnline = c.mode !== 'Offline';
        return `
        <div class="p-3 rounded-xl border border-slate-100 bg-slate-50 flex items-center justify-between text-xs gap-3">
          <div>
            <div class="flex items-center gap-2">
              <span class="px-2 py-0.5 rounded font-bold text-[10px] bg-brand-100 text-brand-700">${c.subject}</span>
              <span class="font-bold text-slate-900">${c.title}</span>
              <span class="px-1.5 py-0.2 rounded text-[10px] font-semibold ${isOnline ? 'bg-blue-100 text-blue-700' : 'bg-amber-100 text-amber-800'}">${isOnline ? '🌐 Online' : '📍 Offline'}</span>
            </div>
            <p class="text-[11px] text-slate-500 mt-1">📅 ${formatDate(c.date)} &bull; ⏰ ${c.startTime} - ${c.endTime}</p>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <button onclick="openClassFeedbackModal('${c.id}', '${(c.title || '').replace(/'/g, "\\'")}', '${c.date}', '${c.mode || 'Online'}')" class="px-2.5 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs flex items-center gap-1">
              <i data-lucide="message-square" class="w-3.5 h-3.5"></i> Remarks
            </button>
            ${isOnline && c.meetingLink ? `<a href="${c.meetingLink}" target="_blank" class="px-3 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs flex items-center gap-1 shrink-0"><i data-lucide="video" class="w-3.5 h-3.5"></i> Join Class</a>` : ''}
          </div>
        </div>
      `;
      }).join('');
    }

    // Homework
    const hwContainer = document.getElementById('student-dash-homework');
    if (!data.homework || data.homework.length === 0) {
      hwContainer.innerHTML = '<div class="text-center py-6 text-slate-400 text-xs">No homework assigned yet.</div>';
    } else {
      hwContainer.innerHTML = data.homework.map(h => {
        let statusBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800">Assigned</span>';
        if (h.status === 'submitted') {
          statusBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800">Submitted</span>';
        } else if (h.status === 'reviewed') {
          statusBadge = `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">Grade: ${h.grade}</span>`;
        } else if (h.status === 'overdue') {
          statusBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800">Overdue</span>';
        }

        return `
          <div class="p-3 rounded-xl border border-slate-100 bg-slate-50 flex items-center justify-between text-xs">
            <div>
              <div class="flex items-center gap-2">
                <span class="font-bold text-slate-900">${h.title}</span>
                ${statusBadge}
              </div>
              <p class="text-[11px] text-slate-500 mt-0.5">Due: ${formatDate(h.dueDate)} &bull; ${h.subject}</p>
            </div>
            <button onclick="openSubmitModal('${h.id}', '${h.title}')" class="px-3 py-1 rounded-lg bg-brand-600 hover:bg-brand-700 text-white font-semibold text-[11px] shrink-0">
              ${h.submissionId ? 'Edit Work' : 'Submit Work'}
            </button>
          </div>
        `;
      }).join('');
    }

    lucide.createIcons();
  } catch (err) {
    console.error('Failed to load student dashboard:', err);
  }
}

// ==============================================================================
// STUDENTS MANAGEMENT
// ==============================================================================

async function loadStudents() {
  if (currentUser.role !== 'teacher') return;
  const search = document.getElementById('student-search-input').value.trim();
  const statusFilter = document.getElementById('student-status-filter').value;

  try {
    let url = `/api/students?status=${statusFilter}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;

    const students = await apiCall(url);
    cachedStudents = students;

    const tbody = document.getElementById('students-table-body');
    if (students.length === 0) {
      tbody.innerHTML = '<tr><td colspan="8" class="py-8 text-center text-slate-400">No students found matching your criteria.</td></tr>';
      return;
    }

    tbody.innerHTML = students.map(s => {
      const isArchived = s.enrollmentStatus === 'archived';
      const statusBadge = isArchived
        ? '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-600">Archived</span>'
        : (s.enrollmentStatus === 'active'
          ? '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-700">Active</span>'
          : '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-700">Inactive</span>');

      return `
        <tr class="hover:bg-slate-50/80 transition">
          <td class="py-3 px-4">
            <div class="font-bold text-slate-900">${s.name}</div>
            <div class="text-[11px] text-slate-400">ID: ${s.id.substring(0, 8)}</div>
          </td>
          <td class="py-3 px-4">
            ${s.username ? `<span class="px-2 py-0.5 rounded-lg bg-indigo-50 text-indigo-700 font-mono text-[11px] font-semibold border border-indigo-100">@${s.username}</span>` : '<span class="text-slate-400 text-[11px] italic">Not set</span>'}
          </td>
          <td class="py-3 px-4">
            <div class="font-medium text-slate-800">${s.grade}</div>
            <div class="text-[11px] text-slate-500">${s.course || 'General'}</div>
          </td>
          <td class="py-3 px-4">
            <div class="flex flex-wrap gap-1">
              ${(s.subjects || []).map(sub => `<span class="px-1.5 py-0.2 rounded text-[10px] bg-slate-100 font-medium text-slate-600">${sub}</span>`).join('')}
            </div>
          </td>
          <td class="py-3 px-4">
            <div>${s.email}</div>
            <div class="text-[11px] text-slate-500">${s.mobile}</div>
          </td>
          <td class="py-3 px-4">
            <div class="font-semibold text-slate-800">${s.guardian?.name || 'N/A'} <span class="text-[10px] text-slate-400 font-normal">(${s.guardian?.relationship || 'Parent'})</span></div>
            <div class="text-[11px] text-slate-500">📞 ${s.guardian?.mobile || 'N/A'}</div>
          </td>
          <td class="py-3 px-4">${statusBadge}</td>
          <td class="py-3 px-4 text-right">
            <div class="flex items-center justify-end gap-1.5">
              <button onclick="viewStudentDetails('${s.id}')" title="View Full Profile" class="p-1 text-slate-500 hover:text-brand-600 rounded hover:bg-slate-100">
                <i data-lucide="eye" class="w-4 h-4"></i>
              </button>
              <button onclick="openPaymentForStudent('${s.id}')" title="Record Received Payment" class="p-1 text-emerald-600 hover:text-emerald-700 rounded hover:bg-emerald-50">
                <i data-lucide="credit-card" class="w-4 h-4"></i>
              </button>
              <button onclick="openSetStudentPasswordModal('${s.id}', '${s.name.replace(/'/g, "\\'")}')" title="Set Student Password" class="p-1 text-slate-500 hover:text-amber-600 rounded hover:bg-slate-100">
                <i data-lucide="key" class="w-4 h-4"></i>
              </button>
              <button onclick="openEditStudent('${s.id}')" title="Edit Student" class="p-1 text-slate-500 hover:text-indigo-600 rounded hover:bg-slate-100">
                <i data-lucide="pencil" class="w-4 h-4"></i>
              </button>
              ${isArchived
          ? `<button onclick="restoreStudent('${s.id}')" title="Restore Student" class="p-1 text-emerald-600 hover:text-emerald-700 rounded hover:bg-emerald-50"><i data-lucide="archive-restore" class="w-4 h-4"></i></button>`
          : `<button onclick="archiveStudent('${s.id}')" title="Archive Student" class="p-1 text-slate-400 hover:text-rose-600 rounded hover:bg-rose-50"><i data-lucide="archive" class="w-4 h-4"></i></button>`
        }
            </div>
          </td>
        </tr>
      `;
    }).join('');

    lucide.createIcons();
  } catch (err) {
    console.error('Failed to load students:', err);
  }
}

async function viewStudentDetails(studentId) {
  try {
    const s = await apiCall(`/api/students/${studentId}`);
    const att = await apiCall(`/api/attendance/student/${studentId}`);
    const feeSum = await apiCall(`/api/fees/student/${studentId}/summary`);

    document.getElementById('detail-student-name').innerText = s.name;
    document.getElementById('detail-student-meta').innerText = `${s.grade} • ${s.course || 'Tuition'}`;

    const container = document.getElementById('detail-student-content');
    container.innerHTML = `
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
        <div class="p-3 bg-slate-50 rounded-xl">
          <span class="text-slate-400 font-semibold uppercase text-[10px]">Enrollment Status</span>
          <p class="font-bold text-slate-800 capitalize mt-0.5">${s.enrollmentStatus}</p>
        </div>
        <div class="p-3 bg-slate-50 rounded-xl">
          <span class="text-slate-400 font-semibold uppercase text-[10px]">Attendance Rate</span>
          <p class="font-bold text-emerald-600 mt-0.5">${att.attendancePercentage}% (${att.present}/${att.totalClasses})</p>
        </div>
        <div class="p-3 bg-slate-50 rounded-xl">
          <span class="text-slate-400 font-semibold uppercase text-[10px]">Total Fees Billed</span>
          <p class="font-bold text-slate-800 mt-0.5">${formatINR(feeSum.totalFees)}</p>
        </div>
        <div class="p-3 bg-slate-50 rounded-xl">
          <span class="text-slate-400 font-semibold uppercase text-[10px]">Current Balance</span>
          <p class="font-bold text-rose-600 mt-0.5">${formatINR(feeSum.balance)}</p>
          ${currentUser.role === 'teacher' ? `
            <button onclick="closeModal('modal-student-details'); openPaymentForStudent('${studentId}', ${feeSum.balance});" class="mt-2 w-full py-1 px-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-[11px] shadow-sm flex items-center justify-center gap-1 transition">
              <i data-lucide="credit-card" class="w-3 h-3"></i> Record Payment
            </button>
          ` : ''}
        </div>
      </div>

      <!-- Contact details -->
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
        <div class="p-4 rounded-xl border border-slate-100 bg-white">
          <h4 class="font-bold text-slate-900 mb-2">Student Information</h4>
          <p><span class="text-slate-400 font-medium">Username:</span> <strong class="text-indigo-700 font-mono">@${s.username || 'Not set'}</strong></p>
          <p class="mt-1"><span class="text-slate-400 font-medium">Email:</span> ${s.email}</p>
          <p class="mt-1"><span class="text-slate-400 font-medium">Mobile:</span> ${s.mobile}</p>
          <p class="mt-1"><span class="text-slate-400 font-medium">Subjects:</span> ${(s.subjects || []).join(', ')}</p>
        </div>

        <div class="p-4 rounded-xl border border-slate-100 bg-white">
          <h4 class="font-bold text-slate-900 mb-2">Parent / Guardian (Teacher View Only)</h4>
          <p><span class="text-slate-400 font-medium">Name:</span> ${s.guardian?.name || 'N/A'} (${s.guardian?.relationship || 'Parent'})</p>
          <p class="mt-1"><span class="text-slate-400 font-medium">Mobile:</span> ${s.guardian?.mobile || 'N/A'}</p>
          <p class="mt-1"><span class="text-slate-400 font-medium">Email:</span> ${s.guardian?.email || 'N/A'}</p>
        </div>
      </div>

      <!-- Teacher Notes -->
      <div class="p-4 rounded-xl border border-slate-100 bg-slate-50 text-xs">
        <h4 class="font-bold text-slate-900 mb-1">Teacher Notes & Guidance</h4>
        <p class="text-slate-600">${s.notes || 'No notes added for this student.'}</p>
      </div>
    `;

    openModal('modal-student-details');
    lucide.createIcons();
  } catch (err) {
    alert('Error loading student profile: ' + err.message);
  }
}

function openAddStudentModal() {
  document.getElementById('student-form-id').value = '';
  document.getElementById('student-modal-title').innerText = 'Add New Student';
  document.getElementById('s-name').value = '';
  document.getElementById('s-username').value = '';
  document.getElementById('s-grade').value = '';
  document.getElementById('s-course').value = '';
  document.getElementById('s-subjects').value = '';
  document.getElementById('s-email').value = '';
  document.getElementById('s-mobile').value = '';
  document.getElementById('g-name').value = '';
  document.getElementById('g-relationship').value = 'Parent';
  document.getElementById('g-mobile').value = '';
  document.getElementById('g-email').value = '';
  document.getElementById('s-status').value = 'active';
  document.getElementById('s-notes').value = '';
  openModal('modal-add-student');
}

async function handleSaveStudent(e) {
  e.preventDefault();
  const formId = document.getElementById('student-form-id').value;
  const usernameVal = document.getElementById('s-username').value.trim();
  const payload = {
    name: document.getElementById('s-name').value.trim(),
    username: usernameVal || undefined,
    grade: document.getElementById('s-grade').value.trim(),
    course: document.getElementById('s-course').value.trim(),
    subjects: document.getElementById('s-subjects').value.split(',').map(s => s.trim()).filter(Boolean),
    email: document.getElementById('s-email').value.trim(),
    mobile: document.getElementById('s-mobile').value.trim(),
    guardian: {
      name: document.getElementById('g-name').value.trim(),
      mobile: document.getElementById('g-mobile').value.trim(),
      email: document.getElementById('g-email').value.trim() || undefined,
      relationship: document.getElementById('g-relationship').value.trim() || 'Parent'
    },
    enrollmentStatus: document.getElementById('s-status').value,
    notes: document.getElementById('s-notes').value.trim()
  };

  try {
    if (formId) {
      await apiCall(`/api/students/${formId}`, 'PUT', payload);
    } else {
      await apiCall('/api/students', 'POST', payload);
    }
    closeModal('modal-add-student');
    loadStudents();
  } catch (err) {
    alert('Error saving student: ' + err.message);
  }
}

function openEditStudent(studentId) {
  const s = cachedStudents.find(x => x.id === studentId);
  if (!s) return;

  document.getElementById('student-form-id').value = s.id;
  document.getElementById('student-modal-title').innerText = 'Edit Student Profile';
  document.getElementById('s-name').value = s.name;
  document.getElementById('s-username').value = s.username || '';
  document.getElementById('s-grade').value = s.grade;
  document.getElementById('s-course').value = s.course || '';
  document.getElementById('s-subjects').value = (s.subjects || []).join(', ');
  document.getElementById('s-email').value = s.email;
  document.getElementById('s-mobile').value = s.mobile;
  document.getElementById('g-name').value = s.guardian?.name || '';
  document.getElementById('g-relationship').value = s.guardian?.relationship || 'Parent';
  document.getElementById('g-mobile').value = s.guardian?.mobile || '';
  document.getElementById('g-email').value = s.guardian?.email || '';
  document.getElementById('s-status').value = s.enrollmentStatus || 'active';
  document.getElementById('s-notes').value = s.notes || '';

  openModal('modal-add-student');
}

async function archiveStudent(studentId) {
  if (!confirm('Are you sure you want to archive this student? All attendance, homework, and fee records will be safely preserved.')) return;
  try {
    await apiCall(`/api/students/${studentId}/archive`, 'POST');
    loadStudents();
  } catch (err) {
    alert('Error archiving student: ' + err.message);
  }
}

async function restoreStudent(studentId) {
  try {
    await apiCall(`/api/students/${studentId}/restore`, 'POST');
    loadStudents();
  } catch (err) {
    alert('Error restoring student: ' + err.message);
  }
}

// ==============================================================================
// CLASSES, MONTH NAVIGATION & FEEDBACK
// ==============================================================================

function updateClassMonthLabel() {
  const date = new Date(classSelectedYear, classSelectedMonth - 1, 1);
  const label = date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
  const el = document.getElementById('class-month-label');
  if (el) el.innerText = label;
}

function changeClassMonth(delta) {
  classSelectedMonth += delta;
  if (classSelectedMonth > 12) {
    classSelectedMonth = 1;
    classSelectedYear += 1;
  } else if (classSelectedMonth < 1) {
    classSelectedMonth = 12;
    classSelectedYear -= 1;
  }
  updateClassMonthLabel();
  loadClasses();
}

function goToCurrentMonth() {
  const now = new Date();
  classSelectedYear = now.getFullYear();
  classSelectedMonth = now.getMonth() + 1;
  updateClassMonthLabel();
  loadClasses();
}

function toggleStudentPicker(type) {
  if (type === 'class') {
    const isDedicated = document.querySelector('input[name="c-assign-type"]:checked')?.value === 'dedicated';
    const picker = document.getElementById('c-students-picker');
    if (picker) {
      if (isDedicated) picker.classList.remove('hidden');
      else picker.classList.add('hidden');
    }
  } else if (type === 'hw') {
    const isDedicated = document.querySelector('input[name="hw-assign-type"]:checked')?.value === 'dedicated';
    const picker = document.getElementById('hw-students-picker');
    if (picker) {
      if (isDedicated) picker.classList.remove('hidden');
      else picker.classList.add('hidden');
    }
  }
}

function selectAllPickerStudents(type, selectAll) {
  const inputName = type === 'class' ? 'c-dedicated-student' : 'hw-dedicated-student';
  const checkboxes = document.querySelectorAll(`input[name="${inputName}"]`);
  checkboxes.forEach(cb => { cb.checked = selectAll; });
}

async function populateStudentPickerCheckboxes(containerId, inputName) {
  const container = document.getElementById(containerId);
  if (!container) return;
  if (cachedStudents.length === 0) {
    cachedStudents = await apiCall('/api/students');
  }
  if (cachedStudents.length === 0) {
    container.innerHTML = '<div class="text-slate-400 text-[11px] p-2">No active students registered yet.</div>';
    return;
  }
  container.innerHTML = cachedStudents.map(s => `
    <label class="flex items-center gap-2 p-1.5 hover:bg-slate-50 rounded-lg cursor-pointer text-xs transition border border-transparent hover:border-slate-200">
      <input type="checkbox" name="${inputName}" value="${s.id}" class="rounded text-brand-600 focus:ring-brand-500 w-4 h-4">
      <span class="font-semibold text-slate-800">${s.name}</span>
      ${s.username ? `<span class="text-[11px] text-brand-600 font-mono">(@${s.username})</span>` : ''}
      <span class="text-[11px] text-slate-400 ml-auto">(${s.grade || 'Student'})</span>
    </label>
  `).join('');
}

function initClassStudentPicker() {
  const allRadio = document.querySelector('input[name="c-assign-type"][value="all"]');
  if (allRadio) allRadio.checked = true;
  const picker = document.getElementById('c-students-picker');
  if (picker) picker.classList.add('hidden');
  populateStudentPickerCheckboxes('c-students-checkboxes', 'c-dedicated-student');
}

function initHomeworkStudentPicker() {
  const allRadio = document.querySelector('input[name="hw-assign-type"][value="all"]');
  if (allRadio) allRadio.checked = true;
  const picker = document.getElementById('hw-students-picker');
  if (picker) picker.classList.add('hidden');
  populateStudentPickerCheckboxes('hw-students-checkboxes', 'hw-dedicated-student');
}

function toggleClassModeFields() {
  const mode = document.getElementById('c-mode').value;
  const wrapper = document.getElementById('c-meeting-link-wrapper');
  const linkInput = document.getElementById('c-meeting-link');
  if (mode === 'Offline') {
    if (wrapper) wrapper.classList.add('hidden');
    if (linkInput) linkInput.value = '';
  } else {
    if (wrapper) wrapper.classList.remove('hidden');
  }
}

async function loadClasses() {
  updateClassMonthLabel();
  const subject = document.getElementById('class-subject-filter').value;
  try {
    let url = `/api/classes?year=${classSelectedYear}&month=${classSelectedMonth}`;
    if (subject && subject !== 'all') url += `&subject=${encodeURIComponent(subject)}`;
    const classes = await apiCall(url);

    const grid = document.getElementById('classes-grid');
    if (classes.length === 0) {
      grid.innerHTML = '<div class="col-span-full py-12 text-center text-slate-400 text-xs">No scheduled classes found for this month.</div>';
      return;
    }

    grid.innerHTML = classes.map(c => {
      const isPast = new Date(c.date) < new Date(new Date().setHours(0, 0, 0, 0));
      const isOnline = c.mode !== 'Offline';

      return `
        <div class="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 flex flex-col justify-between space-y-4 hover:shadow-md transition">
          <div>
            <div class="flex items-center justify-between gap-2 mb-2">
              <span class="px-2.5 py-0.5 rounded-full font-bold text-[10px] bg-brand-50 text-brand-700 uppercase tracking-wider">${c.subject}</span>
              <div class="flex items-center gap-1.5">
                <span class="px-2 py-0.5 rounded-full font-bold text-[10px] ${isOnline ? 'bg-blue-50 text-blue-700' : 'bg-amber-50 text-amber-800'}">
                  ${isOnline ? '🌐 Online' : '📍 Offline'}
                </span>
                ${isPast ? '<span class="text-[10px] font-bold text-slate-400 uppercase">Past</span>' : '<span class="text-[10px] font-bold text-emerald-600 uppercase">Upcoming</span>'}
              </div>
            </div>
            <h4 class="font-bold text-slate-900 text-sm leading-snug">${c.title}</h4>
            ${c.grade ? `<p class="text-[11px] text-slate-500 mt-0.5">Target: ${c.grade}</p>` : ''}
            
            <div class="mt-3 space-y-1 text-xs text-slate-600">
              <div class="flex items-center gap-2">
                <i data-lucide="calendar" class="w-3.5 h-3.5 text-slate-400"></i>
                <span>${formatDate(c.date)}</span>
              </div>
              <div class="flex items-center gap-2">
                <i data-lucide="clock" class="w-3.5 h-3.5 text-slate-400"></i>
                <span>${c.startTime} - ${c.endTime}</span>
              </div>
              <div class="flex items-center gap-2">
                <i data-lucide="${isOnline ? 'video' : 'map-pin'}" class="w-3.5 h-3.5 text-slate-400"></i>
                <span>${isOnline ? 'Online Mode' : 'Offline / In-Person Mode'}</span>
              </div>
              <div class="flex items-center gap-2">
                <i data-lucide="${currentUser.role === 'teacher' ? 'users' : 'user-check'}" class="w-3.5 h-3.5 text-slate-400"></i>
                <span>
                  ${currentUser.role === 'teacher'
                    ? (c.assignedStudents && c.assignedStudents.length > 0
                        ? `Dedicated: <strong class="text-brand-700">${c.assignedStudents.map(s => s.name).join(', ')}</strong>`
                        : 'All Enrolled Students')
                    : `Assigned: <strong class="text-slate-800">${currentUser.name || 'You'}</strong>`
                  }
                </span>
              </div>
            </div>

            ${c.notes ? `<p class="mt-3 p-2.5 rounded-xl bg-slate-50 text-[11px] text-slate-600 border border-slate-100">${c.notes}</p>` : ''}
          </div>

          <div class="pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2">
            <div>
              ${isOnline && c.meetingLink ? `
                <a href="${c.meetingLink}" target="_blank" class="px-3 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs flex items-center gap-1.5 transition">
                  <i data-lucide="video" class="w-3.5 h-3.5"></i>
                  <span>Join Link</span>
                </a>
              ` : (isOnline ? '<span class="text-[11px] text-slate-400">Online (No link)</span>' : '<span class="text-[11px] text-slate-600 font-semibold flex items-center gap-1"><i data-lucide="map-pin" class="w-3 h-3 text-amber-600"></i> In-Person</span>')}
            </div>

            <div class="flex items-center gap-1.5">
              <button onclick="openClassFeedbackModal('${c.id}', '${(c.title || '').replace(/'/g, "\\'")}', '${c.date}', '${c.mode || 'Online'}')" class="px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs flex items-center gap-1 transition" title="Class Remarks & Feedback">
                <i data-lucide="message-square" class="w-3.5 h-3.5 text-brand-600"></i>
                <span>Feedback</span>
              </button>

              ${currentUser.role === 'teacher' ? `
                <button onclick="openAttendanceModal('${c.id}', '${c.title}')" class="px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs flex items-center gap-1">
                  <i data-lucide="clipboard-check" class="w-3.5 h-3.5"></i> Attendance
                </button>
                <button onclick="deleteClass('${c.id}')" title="Delete Class" class="p-1.5 text-slate-400 hover:text-rose-600 rounded-lg hover:bg-rose-50">
                  <i data-lucide="trash-2" class="w-4 h-4"></i>
                </button>
              ` : ''}
            </div>
          </div>
        </div>
      `;
    }).join('');

    lucide.createIcons();
  } catch (err) {
    console.error('Failed to load classes:', err);
  }
}

async function handleSaveClass(e) {
  e.preventDefault();
  const mode = document.getElementById('c-mode').value;
  const assignType = document.querySelector('input[name="c-assign-type"]:checked')?.value || 'all';
  let assignedStudentIds = [];
  if (assignType === 'dedicated') {
    const checked = document.querySelectorAll('input[name="c-dedicated-student"]:checked');
    assignedStudentIds = Array.from(checked).map(cb => cb.value);
    if (assignedStudentIds.length === 0) {
      alert('Please select at least one dedicated student, or switch to "All Students".');
      return;
    }
  }

  const payload = {
    title: document.getElementById('c-title').value.trim(),
    subject: document.getElementById('c-subject').value.trim(),
    grade: document.getElementById('c-grade').value.trim(),
    mode: mode,
    date: document.getElementById('c-date').value,
    startTime: document.getElementById('c-start-time').value,
    endTime: document.getElementById('c-end-time').value,
    meetingLink: (mode === 'Online' ? document.getElementById('c-meeting-link').value.trim() : '') || undefined,
    notes: document.getElementById('c-notes').value.trim(),
    assignedStudentIds: assignedStudentIds
  };

  try {
    await apiCall('/api/classes', 'POST', payload);
    closeModal('modal-add-class');
    loadClasses();
  } catch (err) {
    alert('Error scheduling class: ' + err.message);
  }
}

// ==============================================================================
// CLASS FEEDBACK & REMARKS
// ==============================================================================

async function openClassFeedbackModal(classId, classTitle, classDate, classMode) {
  activeFeedbackClassId = classId;
  document.getElementById('feedback-class-id').value = classId;
  document.getElementById('feedback-modal-title').innerText = `Feedback: ${classTitle || 'Class Session'}`;
  document.getElementById('feedback-modal-meta').innerText = `${formatDate(classDate)} • Mode: ${classMode || 'Online'}`;
  document.getElementById('feedback-text').value = '';

  const shareContainer = document.getElementById('feedback-share-toggle-container');
  if (currentUser.role === 'teacher') {
    if (shareContainer) shareContainer.classList.remove('hidden');
  } else {
    if (shareContainer) shareContainer.classList.add('hidden');
  }

  openModal('modal-class-feedback');
  await loadClassFeedback(classId);
}

async function loadClassFeedback(classId) {
  const container = document.getElementById('class-feedback-list');
  container.innerHTML = '<div class="text-center py-6 text-slate-400 text-xs">Loading feedback...</div>';

  try {
    const feedbackList = await apiCall(`/api/classes/${classId}/feedback`);
    if (!feedbackList || feedbackList.length === 0) {
      container.innerHTML = '<div class="text-center py-8 text-slate-400 text-xs">No feedback or remarks recorded for this class yet. Be the first to share comments!</div>';
      return;
    }

    container.innerHTML = feedbackList.map(item => {
      const isTeacher = item.authorRole === 'teacher';
      const isMine = item.authorId === currentUser.id;
      const canDelete = currentUser.role === 'teacher' || isMine;

      return `
        <div class="p-3.5 rounded-xl border ${isTeacher ? 'border-brand-200 bg-brand-50/40' : 'border-slate-200 bg-slate-50'} space-y-2 text-xs">
          <div class="flex items-center justify-between gap-2">
            <div class="flex items-center gap-2">
              <span class="px-2 py-0.5 rounded font-bold text-[10px] ${isTeacher ? 'bg-brand-600 text-white' : 'bg-slate-200 text-slate-700'} uppercase">
                ${item.authorRole}
              </span>
              <span class="font-bold text-slate-900">${item.authorName}</span>
              <span class="text-[10px] text-slate-400">${formatDate(item.createdAt)}</span>
            </div>
            
            <div class="flex items-center gap-1.5">
              ${currentUser.role === 'teacher' ? `
                <button onclick="toggleFeedbackSharing('${item.id}', '${classId}')" title="${item.sharedWithStudent ? 'Visible to student (Click to make private)' : 'Private to teacher (Click to share with student)'}" class="px-2 py-0.5 rounded text-[10px] font-semibold flex items-center gap-1 transition ${item.sharedWithStudent ? 'bg-emerald-100 text-emerald-700 hover:bg-emerald-200' : 'bg-slate-200 text-slate-600 hover:bg-slate-300'}">
                  <i data-lucide="${item.sharedWithStudent ? 'eye' : 'eye-off'}" class="w-3 h-3"></i>
                  <span>${item.sharedWithStudent ? 'Shared with Student' : 'Private to Teacher'}</span>
                </button>
              ` : ''}
              
              ${canDelete ? `
                <button onclick="deleteFeedback('${item.id}', '${classId}')" title="Delete Remark" class="p-1 text-slate-400 hover:text-rose-600 rounded">
                  <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                </button>
              ` : ''}
            </div>
          </div>
          <p class="text-slate-700 leading-relaxed whitespace-pre-line text-xs">${item.feedback}</p>
        </div>
      `;
    }).join('');

    lucide.createIcons();
  } catch (err) {
    container.innerHTML = `<div class="p-4 text-center text-rose-600 text-xs">Error loading feedback: ${err.message}</div>`;
  }
}

async function handlePostClassFeedback(e) {
  e.preventDefault();
  const classId = document.getElementById('feedback-class-id').value;
  const feedback = document.getElementById('feedback-text').value.trim();
  const shareToggle = document.getElementById('feedback-share-toggle');
  const sharedWithStudent = shareToggle ? shareToggle.checked : true;

  if (!feedback) return;

  try {
    await apiCall(`/api/classes/${classId}/feedback`, 'POST', {
      feedback,
      sharedWithStudent
    });
    document.getElementById('feedback-text').value = '';
    await loadClassFeedback(classId);
  } catch (err) {
    alert('Error posting feedback: ' + err.message);
  }
}

async function toggleFeedbackSharing(feedbackId, classId) {
  try {
    await apiCall(`/api/classes/feedback/${feedbackId}/share`, 'PUT');
    await loadClassFeedback(classId);
  } catch (err) {
    alert('Error updating feedback visibility: ' + err.message);
  }
}

async function deleteFeedback(feedbackId, classId) {
  if (!confirm('Are you sure you want to remove this feedback remark?')) return;
  try {
    await apiCall(`/api/classes/feedback/${feedbackId}`, 'DELETE');
    await loadClassFeedback(classId);
  } catch (err) {
    alert('Error deleting feedback: ' + err.message);
  }
}

async function deleteClass(classId) {
  if (!confirm('Are you sure you want to delete this class schedule? Associated attendance records will also be removed.')) return;
  try {
    await apiCall(`/api/classes/${classId}`, 'DELETE');
    loadClasses();
  } catch (err) {
    alert('Error deleting class: ' + err.message);
  }
}

// Attendance Roster Modal
async function openAttendanceModal(classId, classTitle) {
  activeRosterClassId = classId;
  document.getElementById('att-class-title').innerText = classTitle || 'Class Attendance';
  const rosterContainer = document.getElementById('att-roster-list');
  rosterContainer.innerHTML = '<div class="text-center py-6 text-slate-400 text-xs">Loading roster...</div>';
  openModal('modal-attendance');

  try {
    const data = await apiCall(`/api/attendance/class/${classId}`);
    document.getElementById('att-class-meta').innerText = `${formatDate(data.classDate)} • ${data.subject}`;

    if (!data.roster || data.roster.length === 0) {
      rosterContainer.innerHTML = '<div class="text-center py-6 text-slate-400 text-xs">No active students assigned to this class session.</div>';
      return;
    }

    rosterContainer.innerHTML = data.roster.map(r => `
      <div class="p-3 rounded-xl border border-slate-100 bg-slate-50 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs student-roster-row" data-student-id="${r.studentId}">
        <div>
          <p class="font-bold text-slate-900">${r.studentName}</p>
          <p class="text-[11px] text-slate-400">${r.grade || 'Tuition'}</p>
        </div>
        <div class="flex items-center gap-2">
          <select class="roster-status text-xs px-2.5 py-1 rounded-lg border border-slate-200 bg-white font-semibold">
            <option value="present" ${r.status === 'present' ? 'selected' : ''}>✅ Present</option>
            <option value="absent" ${r.status === 'absent' ? 'selected' : ''}>❌ Absent</option>
            <option value="late" ${r.status === 'late' ? 'selected' : ''}>⏰ Late</option>
            <option value="excused" ${r.status === 'excused' ? 'selected' : ''}>ℹ️ Excused</option>
          </select>
          <input type="text" placeholder="Remarks..." value="${r.remarks || ''}" class="roster-remarks text-xs px-2.5 py-1 rounded-lg border border-slate-200 bg-white w-32 sm:w-40">
        </div>
      </div>
    `).join('');
  } catch (err) {
    rosterContainer.innerHTML = `<div class="p-4 text-center text-rose-600 text-xs">Error: ${err.message}</div>`;
  }
}

function markAllAttendance(status) {
  document.querySelectorAll('.roster-status').forEach(select => {
    select.value = status;
  });
}

async function saveAttendanceBulk() {
  if (!activeRosterClassId) return;
  const rows = document.querySelectorAll('.student-roster-row');
  const records = [];

  rows.forEach(row => {
    const studentId = row.getAttribute('data-student-id');
    const status = row.querySelector('.roster-status').value;
    const remarks = row.querySelector('.roster-remarks').value.trim();
    records.push({ studentId, status, remarks });
  });

  try {
    await apiCall('/api/attendance/bulk', 'POST', {
      classId: activeRosterClassId,
      records: records
    });
    closeModal('modal-attendance');
    alert('Attendance saved successfully!');
  } catch (err) {
    alert('Error saving attendance: ' + err.message);
  }
}

// ==============================================================================
// HOMEWORK & SUBMISSIONS
// ==============================================================================

async function loadHomework() {
  const subject = document.getElementById('hw-subject-filter').value;
  try {
    let url = '/api/homework';
    if (subject && subject !== 'all') url += `?subject=${encodeURIComponent(subject)}`;
    const hwList = await apiCall(url);

    const container = document.getElementById('homework-list');
    if (hwList.length === 0) {
      container.innerHTML = '<div class="py-12 text-center text-slate-400 text-xs">No homework assignments found.</div>';
      return;
    }

    container.innerHTML = hwList.map(h => {
      const isTeacher = currentUser.role === 'teacher';
      const isPast = new Date(h.dueDate) < new Date(new Date().setHours(0, 0, 0, 0));

      let studentSubmissionBadge = '';
      if (!isTeacher) {
        if (h.submission) {
          if (h.submission.status === 'reviewed') {
            studentSubmissionBadge = `<span class="px-2.5 py-0.5 rounded-full font-bold text-xs bg-emerald-100 text-emerald-800">Reviewed • Grade: ${h.submission.grade}</span>`;
          } else {
            studentSubmissionBadge = `<span class="px-2.5 py-0.5 rounded-full font-bold text-xs bg-blue-100 text-blue-800">Submitted</span>`;
          }
        } else {
          studentSubmissionBadge = isPast
            ? `<span class="px-2.5 py-0.5 rounded-full font-bold text-xs bg-rose-100 text-rose-800">Overdue</span>`
            : `<span class="px-2.5 py-0.5 rounded-full font-bold text-xs bg-amber-100 text-amber-800">Assigned</span>`;
        }
      }

      return `
        <div class="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 space-y-3 hover:shadow-md transition">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <div class="flex items-center gap-2">
                <span class="px-2 py-0.5 rounded font-bold text-[10px] bg-indigo-50 text-indigo-700 uppercase">${h.subject}</span>
                <h4 class="font-bold text-slate-900 text-sm">${h.title}</h4>
              </div>
              <p class="text-xs text-slate-500 mt-1">
                Due Date: <strong class="${isPast ? 'text-rose-600' : 'text-slate-800'}">${formatDate(h.dueDate)}</strong> &bull; Total Marks: ${h.totalMarks || 100}
                &bull;
                ${isTeacher
                  ? (h.assignedStudents && h.assignedStudents.length > 0
                      ? `Dedicated: <strong class="text-brand-700">${h.assignedStudents.map(s => s.name).join(', ')}</strong>`
                      : '<span class="text-slate-600 font-medium">All Enrolled Students</span>')
                  : `Assigned: <strong class="text-slate-800">${currentUser.name || 'You'}</strong>`
                }
              </p>
            </div>
            <div>
              ${isTeacher
          ? `<span class="px-2.5 py-1 rounded-xl bg-slate-100 font-semibold text-xs text-slate-700">${h.totalSubmissions || 0} Submissions (${h.pendingReviews || 0} pending review)</span>`
          : studentSubmissionBadge
        }
            </div>
          </div>

          <div class="p-3 bg-slate-50 rounded-xl text-xs text-slate-700 leading-relaxed whitespace-pre-line border border-slate-100">
            ${h.instructions}
          </div>

          ${h.attachmentUrl ? `
            <div class="flex items-center gap-2 text-xs">
              <i data-lucide="paperclip" class="w-3.5 h-3.5 text-brand-600"></i>
              <a href="${h.attachmentUrl}" target="_blank" class="font-medium text-brand-600 hover:underline">
                Download Attached Reference: ${h.attachmentName || 'Handout File'}
              </a>
            </div>
          ` : ''}

          <!-- Student submission details with name beside file -->
          ${!isTeacher && h.submission ? `
            <div class="p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs space-y-2">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <i data-lucide="file-check-2" class="w-4 h-4 text-emerald-600 shrink-0"></i>
                  <span class="font-bold text-slate-900">${currentUser.name || 'You'}:</span>
                  ${h.submission.attachmentUrl ? `
                    <a href="${h.submission.attachmentUrl}" target="_blank" class="font-semibold text-brand-600 hover:underline flex items-center gap-1">
                      <span>📄 ${h.submission.attachmentName || 'Submitted Solution File'}</span>
                      <i data-lucide="external-link" class="w-3 h-3"></i>
                    </a>
                  ` : `<span class="text-slate-700 italic">${h.submission.submissionText || 'Text submission'}</span>`}
                </div>
                <span class="text-[10px] text-slate-400">${formatDate(h.submission.submittedAt)}</span>
              </div>
              ${h.submission.feedback ? `
                <div class="pt-2 border-t border-slate-200 text-xs text-emerald-800">
                  <p class="font-bold text-emerald-900">Teacher Evaluation (Grade: ${h.submission.grade || 'Reviewed'}):</p>
                  <p class="mt-0.5">${h.submission.feedback}</p>
                </div>
              ` : ''}
            </div>
          ` : ''}

          <!-- Footer Actions -->
          <div class="pt-2 border-t border-slate-100 flex items-center justify-between">
            <span class="text-[11px] text-slate-400">Assigned: ${formatDate(h.assignedDate || h.createdAt)}</span>
            <div class="flex items-center gap-2">
              ${isTeacher ? `
                <button onclick="openSubmissionsModal('${h.id}', '${h.title}')" class="px-3.5 py-1.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-semibold text-xs shadow-sm flex items-center gap-1.5">
                  <i data-lucide="check-square" class="w-3.5 h-3.5"></i> View Submissions & Grade
                </button>
                <button onclick="deleteHomework('${h.id}')" title="Delete Assignment" class="p-1.5 text-slate-400 hover:text-rose-600 rounded-lg hover:bg-rose-50">
                  <i data-lucide="trash-2" class="w-4 h-4"></i>
                </button>
              ` : `
                <button onclick="openSubmitModal('${h.id}', '${h.title}')" class="px-4 py-1.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-semibold text-xs shadow-sm flex items-center gap-1.5">
                  <i data-lucide="upload" class="w-3.5 h-3.5"></i> ${h.submission ? 'Update Submission' : 'Submit Homework'}
                </button>
              `}
            </div>
          </div>
        </div>
      `;
    }).join('');

    lucide.createIcons();
  } catch (err) {
    console.error('Failed to load homework:', err);
  }
}

async function handleSaveHomework(e) {
  e.preventDefault();
  const assignType = document.querySelector('input[name="hw-assign-type"]:checked')?.value || 'all';
  let assignedStudentIds = [];
  if (assignType === 'dedicated') {
    const checked = document.querySelectorAll('input[name="hw-dedicated-student"]:checked');
    assignedStudentIds = Array.from(checked).map(cb => cb.value);
    if (assignedStudentIds.length === 0) {
      alert('Please select at least one dedicated student, or switch to "All Students".');
      return;
    }
  }

  const payload = {
    title: document.getElementById('hw-title').value.trim(),
    subject: document.getElementById('hw-subject').value.trim(),
    instructions: document.getElementById('hw-instructions').value.trim(),
    totalMarks: parseInt(document.getElementById('hw-total-marks').value) || 100,
    assignedDate: document.getElementById('hw-assigned-date').value || undefined,
    dueDate: document.getElementById('hw-due-date').value,
    attachmentUrl: document.getElementById('hw-attachment-url').value.trim() || undefined,
    assignedStudentIds: assignedStudentIds
  };

  try {
    await apiCall('/api/homework', 'POST', payload);
    closeModal('modal-add-homework');
    loadHomework();
  } catch (err) {
    alert('Error creating homework: ' + err.message);
  }
}

async function deleteHomework(hwId) {
  if (!confirm('Are you sure you want to delete this homework assignment and all student submissions?')) return;
  try {
    await apiCall(`/api/homework/${hwId}`, 'DELETE');
    loadHomework();
  } catch (err) {
    alert('Error deleting homework: ' + err.message);
  }
}

// Student Submit Homework (File Upload & Link Supported)
async function handleSubmissionFileUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  const maxBytes = 25 * 1024 * 1024; // 25 MB
  if (file.size > maxBytes) {
    alert(`File size (${(file.size / (1024 * 1024)).toFixed(2)} MB) exceeds the 25 MB limit. Please select a smaller file.`);
    event.target.value = '';
    return;
  }

  const statusDiv = document.getElementById('sub-file-status');
  const label = document.getElementById('sub-file-label');
  if (statusDiv) {
    statusDiv.classList.remove('hidden');
    statusDiv.innerHTML = `<span>⏳ Uploading <strong>${file.name}</strong> (${(file.size / (1024 * 1024)).toFixed(2)} MB)...</span>`;
  }

  const formData = new FormData();
  formData.append('file', file);

  const token = localStorage.getItem('sms_auth_token');
  try {
    const res = await fetch('/api/homework/upload', {
      method: 'POST',
      headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      body: formData
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Upload failed');

    document.getElementById('sub-uploaded-url').value = data.url;
    document.getElementById('sub-uploaded-filename').value = data.filename;

    if (label) label.innerText = `Selected: ${file.name}`;
    if (statusDiv) {
      statusDiv.classList.remove('hidden');
      statusDiv.innerHTML = `✅ Uploaded successfully: <strong>${file.name}</strong> (${data.sizeFormatted || 'Ready'})`;
    }
  } catch (err) {
    if (statusDiv) {
      statusDiv.classList.remove('hidden');
      statusDiv.innerHTML = `<span class="text-rose-600">❌ Error: ${err.message}</span>`;
    }
    alert('Failed to upload file: ' + err.message);
  }
}

function openSubmitModal(hwId, hwTitle) {
  document.getElementById('submit-hw-id').value = hwId;
  document.getElementById('submit-hw-title').innerText = hwTitle;
  document.getElementById('sub-text').value = '';
  document.getElementById('sub-url').value = '';
  document.getElementById('sub-uploaded-url').value = '';
  document.getElementById('sub-uploaded-filename').value = '';
  const fileInput = document.getElementById('sub-file-input');
  if (fileInput) fileInput.value = '';
  const statusDiv = document.getElementById('sub-file-status');
  if (statusDiv) {
    statusDiv.classList.add('hidden');
    statusDiv.innerHTML = '';
  }
  const fileLabel = document.getElementById('sub-file-label');
  if (fileLabel) fileLabel.innerText = 'Click to select file';

  openModal('modal-submit-homework');
}

async function handleSubmitHomework(e) {
  e.preventDefault();
  const hwId = document.getElementById('submit-hw-id').value;
  const uploadedUrl = document.getElementById('sub-uploaded-url').value.trim();
  const uploadedFilename = document.getElementById('sub-uploaded-filename').value.trim();
  const pastedUrl = document.getElementById('sub-url').value.trim();
  const textNotes = document.getElementById('sub-text').value.trim();

  const attachmentUrl = uploadedUrl || pastedUrl || undefined;
  const attachmentName = uploadedFilename || (pastedUrl ? 'External Link Solution' : undefined);

  if (!attachmentUrl && !textNotes) {
    alert('Please either upload a solution file, paste a solution link, or enter your solution text.');
    return;
  }

  const payload = {
    homeworkId: hwId,
    submissionText: textNotes || undefined,
    attachmentUrl: attachmentUrl,
    attachmentName: attachmentName
  };

  try {
    await apiCall('/api/homework/submit', 'POST', payload);
    closeModal('modal-submit-homework');
    alert('Homework submitted successfully!');
    if (currentTab === 'homework') loadHomework();
    else if (currentTab === 'student-dashboard') loadStudentDashboard();
  } catch (err) {
    alert('Error submitting homework: ' + err.message);
  }
}

// Teacher Review Submissions Modal
async function openSubmissionsModal(hwId, hwTitle) {
  document.getElementById('submissions-modal-title').innerText = `Submissions for: ${hwTitle}`;
  const container = document.getElementById('submissions-list-container');
  container.innerHTML = '<div class="text-center py-6 text-slate-400 text-xs">Loading submissions...</div>';
  openModal('modal-view-submissions');

  try {
    const subs = await apiCall(`/api/homework/${hwId}/submissions`);
    if (subs.length === 0) {
      container.innerHTML = '<div class="text-center py-8 text-slate-400 text-xs">No students have submitted this homework yet.</div>';
      return;
    }

    container.innerHTML = subs.map(s => `
      <div class="p-4 rounded-xl border border-slate-200 bg-slate-50 space-y-3 text-xs">
        <div class="flex items-center justify-between">
          <div>
            <h4 class="font-bold text-slate-900">${s.studentName}</h4>
            <p class="text-[11px] text-slate-400">${s.studentGrade} &bull; Submitted: ${formatDate(s.submittedAt)}</p>
          </div>
          <span class="px-2.5 py-0.5 rounded-full font-bold text-[10px] uppercase ${s.status === 'reviewed' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}">
            ${s.status}
          </span>
        </div>

        <div class="p-3 bg-white rounded-xl border border-slate-100 text-slate-700 whitespace-pre-line leading-relaxed">
          ${s.submissionText}
        </div>

        ${s.attachmentUrl ? `
          <div class="flex items-center gap-2 p-2.5 bg-brand-50/60 border border-brand-200/70 rounded-xl">
            <i data-lucide="file-text" class="w-4 h-4 text-brand-600 shrink-0"></i>
            <span class="font-bold text-slate-900">${s.studentName}${s.studentUsername ? ' (@' + s.studentUsername + ')' : ''}:</span>
            <a href="${s.attachmentUrl}" target="_blank" class="font-semibold text-brand-600 hover:underline flex items-center gap-1 truncate">
              <span>${s.attachmentName || 'View Attachment / Link'}</span>
              <i data-lucide="external-link" class="w-3 h-3"></i>
            </a>
          </div>
        ` : ''}

        <!-- Grade & Feedback Form -->
        <div class="pt-3 border-t border-slate-200 flex flex-col sm:flex-row gap-2 items-center">
          <input type="text" id="grade-input-${s.id}" placeholder="Grade / Marks (e.g. 45/50 or A+)" value="${s.grade || ''}" class="w-full sm:w-48 px-3 py-1.5 rounded-lg border border-slate-200 bg-white font-bold text-slate-800">
          <input type="text" id="feedback-input-${s.id}" placeholder="Teacher feedback / comments..." value="${s.feedback || ''}" class="flex-1 px-3 py-1.5 rounded-lg border border-slate-200 bg-white text-slate-700">
          <button onclick="saveReview('${s.id}')" class="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-semibold shrink-0 shadow-sm">
            Save Review
          </button>
        </div>
      </div>
    `).join('');

    lucide.createIcons();
  } catch (err) {
    container.innerHTML = `<div class="p-4 text-center text-rose-600 text-xs">Error: ${err.message}</div>`;
  }
}

async function saveReview(submissionId) {
  const grade = document.getElementById(`grade-input-${submissionId}`).value.trim();
  const feedback = document.getElementById(`feedback-input-${submissionId}`).value.trim();

  if (!grade) {
    alert('Please enter a grade or marks for this submission.');
    return;
  }

  try {
    await apiCall(`/api/homework/submissions/${submissionId}/review`, 'POST', { grade, feedback });
    alert('Review saved and student notified!');
    if (currentTab === 'dashboard') loadTeacherDashboard();
    else if (currentTab === 'homework') loadHomework();
  } catch (err) {
    alert('Error saving review: ' + err.message);
  }
}

// ==============================================================================
// EXAMS & ASSESSMENTS
// ==============================================================================

async function loadExams() {
  try {
    const exams = await apiCall('/api/exams');
    const grid = document.getElementById('exams-grid');

    if (exams.length === 0) {
      grid.innerHTML = '<div class="col-span-full py-12 text-center text-slate-400 text-xs">No exams or tests scheduled.</div>';
      return;
    }

    grid.innerHTML = exams.map(e => `
      <div class="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 flex flex-col justify-between space-y-4 hover:shadow-md transition">
        <div>
          <div class="flex items-center justify-between mb-2">
            <span class="px-2.5 py-0.5 rounded-full font-bold text-[10px] bg-indigo-50 text-indigo-700 uppercase">${e.subject}</span>
            <span class="text-xs font-bold text-slate-700">${e.totalMarks || 100} Marks</span>
          </div>
          <h4 class="font-bold text-slate-900 text-sm leading-snug">${e.title}</h4>
          ${e.grade ? `<p class="text-[11px] text-slate-500 mt-0.5">${e.grade}</p>` : ''}

          <div class="mt-3 space-y-1 text-xs text-slate-600">
            <div class="flex items-center gap-2">
              <i data-lucide="calendar" class="w-3.5 h-3.5 text-slate-400"></i>
              <span>${formatDate(e.date)} ${e.startTime ? `at ${e.startTime}` : ''}</span>
            </div>
            <div class="flex items-center gap-2">
              <i data-lucide="clock" class="w-3.5 h-3.5 text-slate-400"></i>
              <span>Duration: ${e.durationMinutes || 60} mins</span>
            </div>
          </div>

          ${e.syllabus ? `
            <div class="mt-3 p-2.5 rounded-xl bg-slate-50 border border-slate-100 text-[11px] text-slate-600">
              <strong class="text-slate-800">Syllabus:</strong> ${e.syllabus}
            </div>
          ` : ''}
        </div>

        <div class="pt-3 border-t border-slate-100 flex items-center justify-between gap-2">
          ${e.formLink ? `
            <a href="${e.formLink}" target="_blank" class="px-3.5 py-1.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-semibold text-xs flex items-center gap-1.5 shadow-sm transition">
              <i data-lucide="external-link" class="w-3.5 h-3.5"></i>
              <span>Open Google Form</span>
            </a>
          ` : '<span class="text-[11px] text-slate-400">Paper-based / In-class test</span>'}

          ${currentUser.role === 'teacher' ? `
            <button onclick="deleteExam('${e.id}')" title="Delete Exam" class="p-1.5 text-slate-400 hover:text-rose-600 rounded-lg hover:bg-rose-50">
              <i data-lucide="trash-2" class="w-4 h-4"></i>
            </button>
          ` : ''}
        </div>
      </div>
    `).join('');

    lucide.createIcons();
  } catch (err) {
    console.error('Failed to load exams:', err);
  }
}

async function handleSaveExam(e) {
  e.preventDefault();
  const payload = {
    title: document.getElementById('ex-title').value.trim(),
    subject: document.getElementById('ex-subject').value.trim(),
    date: document.getElementById('ex-date').value,
    startTime: document.getElementById('ex-start').value,
    durationMinutes: parseInt(document.getElementById('ex-duration').value) || 60,
    totalMarks: parseInt(document.getElementById('ex-marks').value) || 100,
    syllabus: document.getElementById('ex-syllabus').value.trim(),
    formLink: document.getElementById('ex-link').value.trim() || undefined
  };

  try {
    await apiCall('/api/exams', 'POST', payload);
    closeModal('modal-add-exam');
    loadExams();
  } catch (err) {
    alert('Error scheduling exam: ' + err.message);
  }
}

async function deleteExam(examId) {
  if (!confirm('Are you sure you want to delete this exam?')) return;
  try {
    await apiCall(`/api/exams/${examId}`, 'DELETE');
    loadExams();
  } catch (err) {
    alert('Error deleting exam: ' + err.message);
  }
}

// ==============================================================================
// FEES & MANUAL PAYMENTS (DIRECT UPI PAYMENTS)
// ==============================================================================

async function loadFees() {
  const statusFilter = document.getElementById('fee-status-filter').value;
  try {
    let url = `/api/fees?status=${statusFilter}`;
    const fees = await apiCall(url);
    cachedFees = fees;

    // Fees Table
    const tbody = document.getElementById('fees-table-body');
    if (fees.length === 0) {
      tbody.innerHTML = '<tr><td colspan="8" class="py-8 text-center text-slate-400">No fee records found.</td></tr>';
    } else {
      tbody.innerHTML = fees.map(f => {
        let statusBadge = '';
        if (f.status === 'paid') {
          statusBadge = '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">Paid in Full</span>';
        } else if (f.status === 'partly_paid') {
          statusBadge = '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800">Partly Paid</span>';
        } else if (f.status === 'overdue') {
          statusBadge = '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-100 text-rose-800">Overdue</span>';
        } else {
          statusBadge = '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-700">Unpaid</span>';
        }

        return `
          <tr class="hover:bg-slate-50 transition">
            <td class="py-3 px-4 font-bold text-slate-900">${f.studentName || 'Student'}</td>
            <td class="py-3 px-4 font-medium text-slate-700">${f.period}</td>
            <td class="py-3 px-4 text-slate-500">${formatDate(f.dueDate)}</td>
            <td class="py-3 px-4 text-right font-bold text-slate-900">${formatINR(f.amount)}</td>
            <td class="py-3 px-4 text-right font-medium text-emerald-600">${formatINR(f.paidAmount)}</td>
            <td class="py-3 px-4 text-right font-bold ${f.dueAmount > 0 ? 'text-rose-600' : 'text-slate-400'}">${formatINR(f.dueAmount)}</td>
            <td class="py-3 px-4 text-center">${statusBadge}</td>
            ${currentUser.role === 'teacher' ? `
              <td class="py-3 px-4 text-right">
                <div class="flex items-center justify-end gap-1">
                  ${f.dueAmount > 0 ? `
                    <button onclick="openPaymentForFee('${f.studentId}', '${f.id}', ${f.dueAmount})" title="Record Payment" class="px-2.5 py-1 rounded bg-brand-50 hover:bg-brand-100 text-brand-700 font-semibold text-[11px]">
                      Receive
                    </button>
                  ` : ''}
                  <button onclick="deleteFee('${f.id}')" title="Delete Fee" class="p-1 text-slate-400 hover:text-rose-600 rounded">
                    <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                  </button>
                </div>
              </td>
            ` : '<td class="py-3 px-4 text-right"></td>'}
          </tr>
        `;
      }).join('');
    }

    // Payments Table
    const payments = await apiCall('/api/fees/payments');
    const payTbody = document.getElementById('payments-table-body');
    if (payments.length === 0) {
      payTbody.innerHTML = '<tr><td colspan="7" class="py-8 text-center text-slate-400">No payment transactions recorded yet.</td></tr>';
    } else {
      payTbody.innerHTML = payments.map(p => {
        const isReversal = p.isReversal;
        return `
          <tr class="${isReversal ? 'bg-rose-50/40 text-rose-800' : 'hover:bg-slate-50'} transition">
            <td class="py-3 px-4 text-slate-500">${formatDate(p.paidAt)}</td>
            <td class="py-3 px-4 font-bold text-slate-900">${p.studentName || 'Student'}</td>
            <td class="py-3 px-4 uppercase text-[11px] font-semibold text-slate-600">${p.method}</td>
            <td class="py-3 px-4 font-mono text-[11px] text-slate-600">${p.reference || '—'}</td>
            <td class="py-3 px-4 text-slate-500 text-[11px]">${p.note || (isReversal ? 'Reversal Adjustment' : '—')}</td>
            <td class="py-3 px-4 text-right font-bold ${isReversal ? 'text-rose-600' : 'text-emerald-700'}">
              ${isReversal ? `-${formatINR(p.amount)}` : formatINR(p.amount)}
            </td>
            ${currentUser.role === 'teacher' ? `
              <td class="py-3 px-4 text-right">
                ${!isReversal && !p.reversed ? `
                  <button onclick="openReverseModal('${p.id}', '${p.studentName}', ${p.amount})" class="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200">
                    Reverse
                  </button>
                ` : (p.reversed ? '<span class="text-[10px] font-bold text-slate-400">Reversed</span>' : '')}
              </td>
            ` : '<td class="py-3 px-4 text-right"></td>'}
          </tr>
        `;
      }).join('');
    }

    // If student, render direct UPI QR Code
    if (currentUser.role === 'student') {
      const summary = await apiCall(`/api/fees/student/${currentUser.studentId}/summary`);
      const upiId = summary.upiInfo?.upiId || 'teacher@upi';
      document.getElementById('student-view-upi-id').innerText = upiId;

      // Generate dynamic QR Code for UPI
      const qrContainer = document.getElementById('student-upi-qrcode');
      qrContainer.innerHTML = '';
      if (typeof QRCode !== 'undefined') {
        new QRCode(qrContainer, {
          text: summary.upiInfo.upiUri,
          width: 140,
          height: 140,
          colorDark: '#1e1b4b',
          colorLight: '#ffffff',
          correctLevel: QRCode.CorrectLevel.M
        });
      }
    }

    lucide.createIcons();
  } catch (err) {
    console.error('Failed to load fees:', err);
  }
}

async function handleSaveFee(e) {
  e.preventDefault();
  const payload = {
    studentId: document.getElementById('fee-student-id').value,
    period: document.getElementById('fee-period').value.trim(),
    amount: parseFloat(document.getElementById('fee-amount').value),
    dueDate: document.getElementById('fee-due-date').value,
    description: document.getElementById('fee-desc').value.trim()
  };

  try {
    await apiCall('/api/fees', 'POST', payload);
    closeModal('modal-add-fee');
    loadFees();
  } catch (err) {
    alert('Error creating fee charge: ' + err.message);
  }
}

async function deleteFee(feeId) {
  if (!confirm('Are you sure you want to delete this fee charge? (Only allowed if no payments recorded)')) return;
  try {
    await apiCall(`/api/fees/${feeId}`, 'DELETE');
    loadFees();
  } catch (err) {
    alert('Error: ' + err.message);
  }
}

// Payment Recording Modal
async function preparePaymentModal(studentId = null, feeId = null, defaultAmount = null) {
  // Populate students dropdown
  if (cachedStudents.length === 0) {
    cachedStudents = await apiCall('/api/students');
  }

  const sSelect = document.getElementById('pay-student-id');
  if (sSelect) {
    sSelect.innerHTML = '<option value="">-- Select Student --</option>' +
      cachedStudents.map(s => `<option value="${s.id}">${s.name} ${s.username ? '(@' + s.username + ')' : ''} (${s.grade})</option>`).join('');

    if (studentId) {
      sSelect.value = studentId;
    }
  }

  // Set today's date by default
  const dateInput = document.getElementById('pay-date');
  if (dateInput) {
    dateInput.value = new Date().toISOString().split('T')[0];
  }
  const amountInput = document.getElementById('pay-amount');
  if (amountInput) {
    amountInput.value = defaultAmount !== null && defaultAmount !== undefined ? defaultAmount : '';
  }

  updatePayFeeDropdown(feeId);
  const modal = document.getElementById('modal-record-payment');
  if (modal) modal.classList.remove('hidden');
}

function openPaymentForStudent(studentId, balance) {
  preparePaymentModal(studentId, null, balance);
}

function openPaymentForFee(studentId, feeId, balance) {
  preparePaymentModal(studentId, feeId, balance);
}

function updatePayFeeDropdown(selectedFeeId = null) {
  const studentId = document.getElementById('pay-student-id').value;
  const fSelect = document.getElementById('pay-fee-id');
  fSelect.innerHTML = '<option value="">-- General Payment / Latest Unpaid --</option>';

  if (!studentId) return;
  const studentFees = cachedFees.filter(f => f.studentId === studentId);
  studentFees.forEach(f => {
    const opt = document.createElement('option');
    opt.value = f.id;
    opt.text = `${f.period} (${formatINR(f.dueAmount)} due)`;
    if (f.id === selectedFeeId) opt.selected = true;
    fSelect.appendChild(opt);
  });
}

async function handleRecordPayment(e) {
  e.preventDefault();
  const payload = {
    studentId: document.getElementById('pay-student-id').value,
    feeId: document.getElementById('pay-fee-id').value || undefined,
    amount: parseFloat(document.getElementById('pay-amount').value),
    paidAt: document.getElementById('pay-date').value,
    method: document.getElementById('pay-method').value,
    reference: document.getElementById('pay-ref').value.trim() || undefined,
    note: document.getElementById('pay-note').value.trim() || undefined
  };

  try {
    await apiCall('/api/fees/payments', 'POST', payload);
    closeModal('modal-record-payment');
    alert('Payment recorded successfully into ledger!');
    if (currentTab === 'dashboard') loadTeacherDashboard();
    else loadFees();
  } catch (err) {
    alert('Error recording payment: ' + err.message);
  }
}

// Payment Reversal Modal (Safe Audit Logging)
function openReverseModal(paymentId, studentName, amount) {
  document.getElementById('rev-payment-id').value = paymentId;
  document.getElementById('rev-payment-label').innerText = `${studentName} (${formatINR(amount)})`;
  document.getElementById('rev-reason').value = '';
  openModal('modal-reverse-payment');
}

async function handleReversePayment(e) {
  e.preventDefault();
  const paymentId = document.getElementById('rev-payment-id').value;
  const reason = document.getElementById('rev-reason').value.trim();

  try {
    await apiCall('/api/fees/payments/reverse', 'POST', { paymentId, reason });
    closeModal('modal-reverse-payment');
    alert('Payment reversal logged successfully! Audit history preserved.');
    loadFees();
  } catch (err) {
    alert('Error reversing payment: ' + err.message);
  }
}

function copyUpiId() {
  const upiId = document.getElementById('student-view-upi-id').innerText;
  navigator.clipboard.writeText(upiId).then(() => {
    alert('Teacher UPI ID copied to clipboard: ' + upiId);
  }).catch(() => {
    alert('UPI ID: ' + upiId);
  });
}

// ==============================================================================
// SETTINGS & PROFILE
// ==============================================================================

async function loadSettings() {
  if (currentUser.role !== 'teacher') return;
  try {
    const data = await apiCall('/api/settings/full');
    const p = data.profile || {};
    const s = data.system || {};

    document.getElementById('setting-teacher-name').value = p.teacherName || '';
    document.getElementById('setting-tuition-name').value = p.tuitionName || '';
    document.getElementById('setting-teacher-email').value = p.teacherEmail || '';
    document.getElementById('setting-teacher-phone').value = p.teacherPhone || '';
    document.getElementById('setting-upi-id').value = p.teacherUpiId || '';
    document.getElementById('setting-upi-name').value = p.teacherUpiName || '';
    document.getElementById('setting-tuition-address').value = p.tuitionAddress || '';

    document.getElementById('system-db-engine').innerText = s.databaseEngine || 'MongoDB Atlas';
    document.getElementById('system-timezone').innerText = s.timezone || 'Asia/Kolkata';
    document.getElementById('system-currency').innerText = `${s.currency || '₹'} INR`;
  } catch (err) {
    console.error('Failed to load settings:', err);
  }
}

async function saveSettings(e) {
  e.preventDefault();
  const payload = {
    teacherName: document.getElementById('setting-teacher-name').value.trim(),
    tuitionName: document.getElementById('setting-tuition-name').value.trim(),
    teacherEmail: document.getElementById('setting-teacher-email').value.trim(),
    teacherPhone: document.getElementById('setting-teacher-phone').value.trim(),
    teacherUpiId: document.getElementById('setting-upi-id').value.trim(),
    teacherUpiName: document.getElementById('setting-upi-name').value.trim(),
    tuitionAddress: document.getElementById('setting-tuition-address').value.trim()
  };

  try {
    await apiCall('/api/settings/profile', 'PUT', payload);
    alert('Settings saved successfully!');
    loadSettings();
  } catch (err) {
    alert('Error saving settings: ' + err.message);
  }
}

// ==============================================================================
// PASSWORD MANAGEMENT
// ==============================================================================

function openChangePasswordModal() {
  document.getElementById('cp-current').value = '';
  document.getElementById('cp-new').value = '';
  document.getElementById('cp-confirm').value = '';
  openModal('modal-change-password');
}

async function handleChangePassword(e) {
  e.preventDefault();
  const currentPassword = document.getElementById('cp-current').value;
  const newPassword = document.getElementById('cp-new').value;
  const confirmPassword = document.getElementById('cp-confirm').value;

  if (newPassword !== confirmPassword) {
    alert('New passwords do not match. Please re-enter carefully.');
    return;
  }
  if (newPassword.length < 6) {
    alert('New password must be at least 6 characters long.');
    return;
  }

  try {
    await apiCall('/api/auth/change-password', 'POST', {
      currentPassword,
      newPassword
    });
    closeModal('modal-change-password');
    alert('Password updated successfully! Please remember your new password.');
  } catch (err) {
    alert('Error updating password: ' + err.message);
  }
}

function openSetStudentPasswordModal(studentId, studentName) {
  document.getElementById('set-pw-student-id').value = studentId;
  document.getElementById('set-pw-student-name').innerText = `Student: ${studentName}`;
  document.getElementById('set-pw-new').value = 'Student@2026';
  openModal('modal-set-student-password');
}

async function handleSetStudentPassword(e) {
  e.preventDefault();
  const studentId = document.getElementById('set-pw-student-id').value;
  const newPassword = document.getElementById('set-pw-new').value;

  if (!newPassword || newPassword.length < 6) {
    alert('Student password must be at least 6 characters long.');
    return;
  }

  try {
    await apiCall(`/api/students/${studentId}/set-password`, 'POST', {
      newPassword
    });
    closeModal('modal-set-student-password');
    alert('Student password has been updated successfully!');
  } catch (err) {
    alert('Error setting student password: ' + err.message);
  }
}

// ==============================================================================
// MODAL CONTROLS
// ==============================================================================

function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove('hidden');
    if (modalId === 'modal-add-class') {
      toggleClassModeFields();
      initClassStudentPicker();
      const dateInput = document.getElementById('c-date');
      if (dateInput && !dateInput.value) {
        dateInput.value = new Date().toISOString().split('T')[0];
      }
    }
    if (modalId === 'modal-add-homework') {
      initHomeworkStudentPicker();
      const assignInput = document.getElementById('hw-assigned-date');
      if (assignInput && !assignInput.value) {
        assignInput.value = new Date().toISOString().split('T')[0];
      }
      const dueInput = document.getElementById('hw-due-date');
      if (dueInput && !dueInput.value) {
        dueInput.value = new Date(Date.now() + 7 * 86400000).toISOString().split('T')[0];
      }
    }
    // Pre-populate dropdowns if opening add fee
    if (modalId === 'modal-add-fee') {
      const sSelect = document.getElementById('fee-student-id');
      const renderStudentsForFee = (students) => {
        if (!sSelect) return;
        sSelect.innerHTML = '<option value="">-- Choose a student --</option>' +
          students.map(s => `<option value="${s.id}">${s.name} ${s.username ? '(@' + s.username + ')' : ''} (${s.grade})</option>`).join('');
      };
      if (cachedStudents.length > 0) {
        renderStudentsForFee(cachedStudents);
      } else {
        apiCall('/api/students').then(students => {
          cachedStudents = students;
          renderStudentsForFee(cachedStudents);
        });
      }
      document.getElementById('fee-due-date').value = new Date(Date.now() + 7 * 86400000).toISOString().split('T')[0];
    }
    if (modalId === 'modal-record-payment') {
      const pSelect = document.getElementById('pay-student-id');
      if (!pSelect || pSelect.options.length <= 1) {
        preparePaymentModal();
      }
    }
    lucide.createIcons();
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add('hidden');
  }
}

// Global initialization
window.addEventListener('DOMContentLoaded', () => {
  checkAuth();
});
