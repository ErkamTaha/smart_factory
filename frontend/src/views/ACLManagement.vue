<template>
    <ion-page>
        <ion-header :translucent="true">
            <ion-toolbar color="primary">
                <ion-buttons slot="start">
                    <ion-back-button color="light" default-href="/dashboard"></ion-back-button>
                </ion-buttons>
                <ion-title>ACL Management</ion-title>
                <ion-buttons slot="end">
                    <ion-button color="light" @click="refreshData" :disabled="isLoading" title="Refresh">
                        <ion-icon :icon="refreshOutline" slot="icon-only"></ion-icon>
                    </ion-button>
                </ion-buttons>
            </ion-toolbar>
        </ion-header>

        <ion-content>
            <!-- Loading -->
            <div v-if="isLoading && !aclInfo" class="page-loading">
                <ion-spinner name="crescent" color="primary"></ion-spinner>
                <p>Loading ACL data...</p>
            </div>

            <div v-else>
                <!-- Stats Strip -->
                <ion-card class="stats-card">
                    <ion-card-content>
                        <div class="acl-stats-row">
                            <div class="acl-stat">
                                <span class="acl-stat-val">{{ aclInfo?.total_users ?? '—' }}</span>
                                <span class="acl-stat-label">Users</span>
                            </div>
                            <div class="acl-stat">
                                <span class="acl-stat-val">{{ aclInfo?.total_roles ?? '—' }}</span>
                                <span class="acl-stat-label">Roles</span>
                            </div>
                            <div class="acl-stat">
                                <span class="acl-stat-val">{{ aclInfo?.default_policy ?? '—' }}</span>
                                <span class="acl-stat-label">Policy</span>
                            </div>
                            <div class="acl-stat">
                                <span class="acl-stat-val">{{ aclInfo?.version ?? '—' }}</span>
                                <span class="acl-stat-label">Version</span>
                            </div>
                        </div>
                        <div class="acl-actions">
                            <ion-button fill="outline" size="small" @click="reloadACL" :disabled="isLoading">
                                <ion-icon :icon="refreshOutline" slot="start"></ion-icon>
                                Reload ACL
                            </ion-button>
                            <ion-button fill="outline" size="small" @click="openSessions">
                                <ion-icon :icon="peopleOutline" slot="start"></ion-icon>
                                Sessions
                            </ion-button>
                        </div>
                    </ion-card-content>
                </ion-card>

                <!-- Tabs -->
                <ion-segment v-model="activeTab" class="tab-segment">
                    <ion-segment-button value="users">
                        <ion-label>Users</ion-label>
                    </ion-segment-button>
                    <ion-segment-button value="roles">
                        <ion-label>Roles</ion-label>
                    </ion-segment-button>
                    <ion-segment-button value="permissions">
                        <ion-label>Checker</ion-label>
                    </ion-segment-button>
                </ion-segment>

                <!-- ── USERS TAB ─────────────────────────────────── -->
                <div v-show="activeTab === 'users'">
                    <!-- Create User -->
                    <ion-card>
                        <ion-card-header>
                            <ion-card-title>
                                <ion-icon :icon="personAddOutline"></ion-icon>
                                New User
                            </ion-card-title>
                        </ion-card-header>
                        <ion-card-content>
                            <ion-item>
                                <ion-input v-model="newUser.username" label="Username" label-placement="stacked"
                                    placeholder="e.g. john_doe" clearInput autocomplete="off"></ion-input>
                            </ion-item>
                            <ion-item>
                                <ion-input v-model="newUser.email" label="Email" label-placement="stacked"
                                    type="email" placeholder="e.g. john@example.com" clearInput autocomplete="off"></ion-input>
                            </ion-item>
                            <ion-item>
                                <ion-input v-model="newUser.password" label="Password" label-placement="stacked"
                                    type="password" placeholder="Min 8 characters" clearInput autocomplete="new-password"></ion-input>
                            </ion-item>
                            <ion-item>
                                <ion-select v-model="newUser.roles" multiple label="Roles"
                                    label-placement="stacked" placeholder="Select roles">
                                    <ion-select-option v-for="role in availableRoles" :key="role" :value="role">
                                        {{ role }}
                                    </ion-select-option>
                                </ion-select>
                            </ion-item>
                            <ion-button class="create-btn" @click="createUser"
                                :disabled="!isValidNewUser || isLoading">
                                <ion-icon :icon="personAddOutline" slot="start"></ion-icon>
                                Create User
                            </ion-button>
                        </ion-card-content>
                    </ion-card>

                    <!-- Users List -->
                    <ion-card>
                        <ion-card-header>
                            <ion-card-title>
                                <ion-icon :icon="peopleOutline"></ion-icon>
                                Users
                                <ion-chip color="primary" size="small" style="margin-left:8px">
                                    {{ filteredUsers.length }}
                                </ion-chip>
                            </ion-card-title>
                        </ion-card-header>
                        <ion-card-content style="padding: 0">
                            <ion-searchbar v-model="userSearchTerm" placeholder="Search users..."
                                @ion-input="filterUsers" class="user-search"></ion-searchbar>
                            <ion-list lines="full">
                                <ion-item v-for="user in filteredUsers" :key="user.username">
                                    <div slot="start" class="item-avatar item-avatar-sm">
                                        {{ user.username.charAt(0).toUpperCase() }}
                                    </div>
                                    <ion-label>
                                        <h3>{{ user.username }}</h3>
                                        <p>
                                            <ion-chip v-for="role in user.roles" :key="role"
                                                color="primary" size="small">{{ role }}</ion-chip>
                                            <span v-if="!user.roles?.length" class="text-muted">No roles</span>
                                        </p>
                                        <p class="text-muted">
                                            {{ user.all_permissions?.length || 0 }} permission(s)
                                        </p>
                                    </ion-label>
                                    <ion-button slot="end" fill="clear" size="small" @click="editUser(user)">
                                        <ion-icon :icon="createOutline"></ion-icon>
                                    </ion-button>
                                    <ion-button slot="end" fill="clear" size="small" @click="viewUserDetails(user)">
                                        <ion-icon :icon="eyeOutline"></ion-icon>
                                    </ion-button>
                                    <ion-button slot="end" fill="clear" size="small" color="danger"
                                        @click="deleteUser(user.username)">
                                        <ion-icon :icon="trashOutline"></ion-icon>
                                    </ion-button>
                                </ion-item>
                                <ion-item v-if="filteredUsers.length === 0">
                                    <ion-label class="text-muted" style="text-align:center;padding:16px 0">
                                        No users found
                                    </ion-label>
                                </ion-item>
                            </ion-list>
                        </ion-card-content>
                    </ion-card>
                </div>

                <!-- ── ROLES TAB ─────────────────────────────────── -->
                <div v-show="activeTab === 'roles'">
                    <ion-card v-for="(roleData, roleName) in rolesData" :key="roleName" class="role-card">
                        <ion-card-header>
                            <ion-card-title>
                                <ion-icon :icon="shieldCheckmarkOutline"></ion-icon>
                                {{ roleName }}
                            </ion-card-title>
                            <ion-card-subtitle v-if="roleData.description">
                                {{ roleData.description }}
                            </ion-card-subtitle>
                        </ion-card-header>
                        <ion-card-content>
                            <p class="perm-section-label">Permissions</p>
                            <div v-for="(perm, idx) in roleData.permissions" :key="idx" class="perm-block">
                                <code class="perm-pattern">{{ perm.pattern }}</code>
                                <div class="perm-chips">
                                    <ion-chip v-for="action in perm.allow" :key="action"
                                        color="success" size="small">✓ {{ action }}</ion-chip>
                                    <ion-chip v-for="action in (perm.deny || [])" :key="action"
                                        color="danger" size="small">✗ {{ action }}</ion-chip>
                                </div>
                            </div>
                            <p v-if="!roleData.permissions?.length" class="text-muted">No permissions defined</p>
                        </ion-card-content>
                    </ion-card>
                </div>

                <!-- ── PERMISSION CHECKER TAB ────────────────────── -->
                <div v-show="activeTab === 'permissions'">
                    <ion-card>
                        <ion-card-header>
                            <ion-card-title>
                                <ion-icon :icon="checkmarkCircleOutline"></ion-icon>
                                Permission Checker
                            </ion-card-title>
                        </ion-card-header>
                        <ion-card-content>
                            <ion-item>
                                <ion-select v-model="permCheck.userId" label="User"
                                    label-placement="stacked" placeholder="Select user">
                                    <ion-select-option v-for="user in users" :key="user.username"
                                        :value="user.username">{{ user.username }}</ion-select-option>
                                </ion-select>
                            </ion-item>
                            <ion-item>
                                <ion-input v-model="permCheck.topic" label="Topic"
                                    label-placement="stacked" placeholder="sf/sensors/+/temperature"></ion-input>
                            </ion-item>
                            <ion-item>
                                <ion-select v-model="permCheck.action" label="Action" label-placement="stacked">
                                    <ion-select-option value="subscribe">Subscribe</ion-select-option>
                                    <ion-select-option value="publish">Publish</ion-select-option>
                                </ion-select>
                            </ion-item>
                            <ion-button class="create-btn" @click="checkPermission" :disabled="!isValidPermCheck">
                                <ion-icon :icon="checkmarkCircleOutline" slot="start"></ion-icon>
                                Check
                            </ion-button>

                            <!-- Result -->
                            <div v-if="permCheckResult" class="perm-result"
                                :class="permCheckResult.allowed ? 'perm-result-ok' : 'perm-result-deny'">
                                <ion-icon :icon="permCheckResult.allowed ? checkmarkCircleOutline : closeCircleOutline"
                                    class="perm-result-icon"></ion-icon>
                                <div>
                                    <strong>{{ permCheckResult.allowed ? 'ALLOWED' : 'DENIED' }}</strong>
                                    <p>{{ permCheckResult.username }} · {{ permCheckResult.action }} ·
                                        <code>{{ permCheckResult.topic }}</code>
                                    </p>
                                </div>
                            </div>
                        </ion-card-content>
                    </ion-card>
                </div>
            </div>

            <!-- ── EDIT USER MODAL ──────────────────────────────── -->
            <ion-modal :is-open="showEditModal" @will-dismiss="showEditModal = false">
                <ion-header>
                    <ion-toolbar color="primary">
                        <ion-title>Edit — {{ editingUser?.username }}</ion-title>
                        <ion-buttons slot="end">
                            <ion-button color="light" @click="showEditModal = false">
                                <ion-icon :icon="closeOutline"></ion-icon>
                            </ion-button>
                        </ion-buttons>
                    </ion-toolbar>
                </ion-header>
                <ion-content class="ion-padding">
                    <ion-item v-if="editingUser">
                        <ion-select v-model="editingUser.roles" multiple label="Roles"
                            label-placement="stacked" placeholder="Select roles">
                            <ion-select-option v-for="role in availableRoles" :key="role" :value="role">
                                {{ role }}
                            </ion-select-option>
                        </ion-select>
                    </ion-item>
                    <ion-button class="ion-margin-top" @click="updateUser" :disabled="isLoading">
                        <ion-icon :icon="saveOutline" slot="start"></ion-icon>
                        Save Changes
                    </ion-button>
                </ion-content>
            </ion-modal>

            <!-- ── USER DETAILS MODAL ───────────────────────────── -->
            <ion-modal :is-open="showDetailsModal" @will-dismiss="showDetailsModal = false">
                <ion-header>
                    <ion-toolbar color="primary">
                        <ion-title>{{ selectedUser?.username }}</ion-title>
                        <ion-buttons slot="end">
                            <ion-button color="light" @click="showDetailsModal = false">
                                <ion-icon :icon="closeOutline"></ion-icon>
                            </ion-button>
                        </ion-buttons>
                    </ion-toolbar>
                </ion-header>
                <ion-content class="ion-padding">
                    <div v-if="selectedUser">
                        <!-- Roles -->
                        <p class="modal-section-label">Roles</p>
                        <div class="modal-chips">
                            <ion-chip v-for="role in selectedUser.roles" :key="role" color="primary">
                                {{ role }}
                            </ion-chip>
                            <span v-if="!selectedUser.roles?.length" class="text-muted">No roles assigned</span>
                        </div>

                        <!-- Permissions -->
                        <p class="modal-section-label">
                            Permissions ({{ selectedUser.all_permissions?.length || 0 }})
                        </p>
                        <div v-for="(perm, idx) in selectedUser.all_permissions" :key="idx" class="perm-block">
                            <code class="perm-pattern">{{ perm.pattern }}</code>
                            <div class="perm-chips">
                                <ion-chip v-for="action in perm.allow" :key="action" color="success" size="small">
                                    ✓ {{ action }}
                                </ion-chip>
                                <ion-chip v-for="action in (perm.deny || [])" :key="action" color="danger" size="small">
                                    ✗ {{ action }}
                                </ion-chip>
                            </div>
                        </div>
                        <p v-if="!selectedUser.all_permissions?.length" class="text-muted">No permissions</p>
                    </div>
                </ion-content>
            </ion-modal>

            <!-- ── SESSIONS MODAL ───────────────────────────────── -->
            <ion-modal :is-open="showSessionsModal" @will-dismiss="showSessionsModal = false">
                <ion-header>
                    <ion-toolbar color="primary">
                        <ion-title>Active Sessions</ion-title>
                        <ion-buttons slot="end">
                            <ion-button color="light" @click="showSessionsModal = false">
                                <ion-icon :icon="closeOutline"></ion-icon>
                            </ion-button>
                        </ion-buttons>
                    </ion-toolbar>
                </ion-header>
                <ion-content class="ion-padding">
                    <ion-list v-if="activeSessions.length > 0" lines="full">
                        <ion-item v-for="session in activeSessions" :key="session.id">
                            <div slot="start" class="item-avatar item-avatar-sm">
                                {{ (session.username || session.client_id || '?').charAt(0).toUpperCase() }}
                            </div>
                            <ion-label>
                                <h3>{{ session.username || session.client_id }}</h3>
                                <p>{{ session.subscribed_topics?.length || 0 }} topics · {{ session.ip_address || 'unknown IP' }}</p>
                                <p class="text-muted">Connected: {{ formatTs(session.connected_at) }}</p>
                            </ion-label>
                            <ion-chip slot="end" :color="session.is_active ? 'success' : 'medium'" size="small">
                                {{ session.is_active ? 'Active' : 'Closed' }}
                            </ion-chip>
                        </ion-item>
                    </ion-list>
                    <div v-else class="empty-state">
                        <ion-icon :icon="peopleOutline" size="large" color="medium"></ion-icon>
                        <p>No active sessions</p>
                    </div>
                </ion-content>
            </ion-modal>
        </ion-content>
    </ion-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import {
    IonPage, IonHeader, IonToolbar, IonTitle, IonContent, IonButtons, IonButton,
    IonBackButton, IonIcon, IonCard, IonCardContent, IonCardHeader, IonCardTitle,
    IonCardSubtitle, IonItem, IonLabel, IonInput, IonSelect, IonSelectOption,
    IonChip, IonList, IonSearchbar, IonSegment, IonSegmentButton, IonModal,
    IonSpinner, alertController, toastController
} from '@ionic/vue';
import {
    refreshOutline, shieldCheckmarkOutline, peopleOutline, personAddOutline,
    createOutline, eyeOutline, trashOutline, checkmarkCircleOutline,
    closeCircleOutline, closeOutline, saveOutline
} from 'ionicons/icons';
import apiService from '@/services/api';

// ── State ───────────────────────────────────────────────────
const isLoading = ref(false);
const activeTab = ref('users');

const aclInfo = ref(null);
const users = ref([]);
const rolesData = ref({});
const availableRoles = ref([]);
const activeSessions = ref([]);

const userSearchTerm = ref('');
const filteredUsers = ref([]);

const showEditModal = ref(false);
const showDetailsModal = ref(false);
const showSessionsModal = ref(false);

const newUser = ref({ username: '', email: '', password: '', roles: [] });
const editingUser = ref(null);
const selectedUser = ref(null);
const permCheck = ref({ userId: '', topic: '', action: 'subscribe' });
const permCheckResult = ref(null);

// ── Computed ────────────────────────────────────────────────
const isValidNewUser = computed(() =>
    newUser.value.username.trim() &&
    newUser.value.email.trim() &&
    newUser.value.password.length >= 8 &&
    newUser.value.roles.length > 0
);
const isValidPermCheck = computed(() =>
    permCheck.value.userId && permCheck.value.topic && permCheck.value.action
);

// ── Helpers ─────────────────────────────────────────────────
const showToast = async (message, color = 'primary') => {
    const toast = await toastController.create({
        message,
        duration: 3000,
        position: 'bottom',
        cssClass: `app-toast app-toast-${color}`,
    });
    await toast.present();
};

const formatTs = (ts) => ts ? new Date(ts).toLocaleString() : '—';

// ── Data loading ─────────────────────────────────────────────
const loadACLInfo = async () => {
    const response = await apiService.getACLInfo();
    aclInfo.value = response.data;
};

const loadUsers = async () => {
    const response = await apiService.getAllUsers();
    users.value = response.data || [];
    filteredUsers.value = users.value;
};

const loadRoles = async () => {
    const response = await apiService.getAllRoles();
    rolesData.value = response.data || {};
    availableRoles.value = Object.keys(rolesData.value);
};

const loadSessions = async () => {
    const response = await apiService.getActiveSessions();
    // Response is { sessions: [...], count: N }
    activeSessions.value = response.data?.sessions || response.data || [];
};

const refreshData = async () => {
    isLoading.value = true;
    try {
        await Promise.all([loadACLInfo(), loadUsers(), loadRoles()]);
    } catch (err) {
        showToast('Failed to load ACL data', 'danger');
    } finally {
        isLoading.value = false;
    }
};

// ── User management ──────────────────────────────────────────
const createUser = async () => {
    try {
        await apiService.createUser({
            username: newUser.value.username.trim(),
            email: newUser.value.email.trim(),
            password: newUser.value.password,
            roles: newUser.value.roles,
            custom_permissions: []
        });
        newUser.value = { username: '', email: '', password: '', roles: [] };
        await loadUsers();
        await loadACLInfo();
        showToast('User created', 'success');
    } catch (err) {
        const msg = err.response?.data?.detail || 'Failed to create user';
        showToast(msg, 'danger');
    }
};

const editUser = (user) => {
    editingUser.value = { ...user };
    showEditModal.value = true;
};

const updateUser = async () => {
    try {
        await apiService.updateUser(editingUser.value.username, {
            roles: editingUser.value.roles
        });
        showEditModal.value = false;
        await loadUsers();
        showToast('User updated', 'success');
    } catch (err) {
        showToast('Failed to update user', 'danger');
    }
};

const deleteUser = async (username) => {
    const alert = await alertController.create({
        header: 'Delete User',
        message: `Delete "${username}"? This cannot be undone.`,
        buttons: [
            { text: 'Cancel', role: 'cancel' },
            { text: 'Delete', role: 'destructive' },
        ]
    });
    await alert.present();
    const { role } = await alert.onDidDismiss();
    if (role !== 'destructive') return;

    try {
        await apiService.deleteUser(username);
        await Promise.all([loadUsers(), loadACLInfo()]);
        await showToast('User deleted', 'success');
    } catch (err) {
        console.error('Delete failed:', err);
        await showToast('Failed to delete user', 'danger');
    }
};

const viewUserDetails = (user) => {
    selectedUser.value = user;
    showDetailsModal.value = true;
};

// ── Permission check ─────────────────────────────────────────
const checkPermission = async () => {
    try {
        const result = await apiService.checkPermission({
            username: permCheck.value.userId,
            topic: permCheck.value.topic,
            action: permCheck.value.action
        });
        permCheckResult.value = result.data;
    } catch {
        showToast('Failed to check permission', 'danger');
    }
};

// ── Misc ─────────────────────────────────────────────────────
const filterUsers = () => {
    const term = userSearchTerm.value.toLowerCase();
    filteredUsers.value = term
        ? users.value.filter(u =>
            u.username.toLowerCase().includes(term) ||
            u.roles?.some(r => r.toLowerCase().includes(term))
          )
        : users.value;
};

const reloadACL = async () => {
    try {
        await apiService.reloadACL();
        await refreshData();
        showToast('ACL reloaded', 'success');
    } catch {
        showToast('Failed to reload ACL', 'danger');
    }
};

const openSessions = async () => {
    await loadSessions();
    showSessionsModal.value = true;
};

onMounted(refreshData);
</script>

<style scoped>
/* ── Stats card ──────────────────────────────────────────── */
.stats-card {
  margin: 12px 16px 0;
}

.acl-stats-row {
  display: flex;
  justify-content: space-around;
  margin-bottom: 12px;
}

.acl-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.acl-stat-val {
  font-size: 22px;
  font-weight: 700;
  color: var(--ion-color-dark);
  line-height: 1.1;
  text-transform: capitalize;
}

.acl-stat-label {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--ion-color-medium);
}

.acl-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

/* ── Tabs ────────────────────────────────────────────────── */
.tab-segment {
  margin: 10px 16px 0;
}

/* ── Create button ───────────────────────────────────────── */
.create-btn {
  margin-top: 12px;
}

/* ── Search ──────────────────────────────────────────────── */
.user-search {
  --padding-start: 0;
  padding: 0 8px;
}

/* ── Roles ───────────────────────────────────────────────── */
.role-card {
  margin: 8px 16px;
}

.perm-section-label {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--ion-color-medium);
  margin: 0 0 8px;
}

.perm-block {
  background: var(--ion-color-light);
  border-radius: 8px;
  padding: 8px 10px;
  margin-bottom: 6px;
}

.perm-pattern {
  display: block;
  font-size: 12px;
  font-family: monospace;
  color: var(--ion-color-dark);
  margin-bottom: 5px;
}

.perm-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

/* ── Permission checker result ───────────────────────────── */
.perm-result {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-top: 14px;
  padding: 12px 14px;
  border-radius: 10px;
}

.perm-result-ok   { background: rgba(45, 211, 111, 0.12); color: #1a7a45; }
.perm-result-deny { background: rgba(235, 68, 90, 0.10);  color: #a03040; }

.perm-result-icon { font-size: 24px; flex-shrink: 0; margin-top: 2px; }

.perm-result strong { font-size: 15px; font-weight: 700; display: block; }
.perm-result p { margin: 4px 0 0; font-size: 13px; }
.perm-result code { font-family: monospace; font-size: 12px; }

/* ── Modal sections ──────────────────────────────────────── */
.modal-section-label {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--ion-color-medium);
  margin: 16px 0 6px;
}

.modal-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
</style>
