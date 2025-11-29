<template>
    <ion-page>
        <ion-header>
            <ion-toolbar color="primary">
                <ion-buttons slot="start">
                    <ion-back-button default-href="/"></ion-back-button>
                </ion-buttons>
                <ion-title>ACL Management</ion-title>
                <ion-buttons slot="end">
                    <ion-button @click="refreshData" :disabled="isLoading">
                        <ion-icon :icon="refreshOutline" slot="icon-only"></ion-icon>
                    </ion-button>
                </ion-buttons>
            </ion-toolbar>
        </ion-header>

        <ion-content class="ion-padding">
            <!-- ACL Status Card -->
            <ion-card>
                <ion-card-header>
                    <ion-card-title>
                        <ion-icon :icon="shieldCheckmarkOutline"></ion-icon>
                        ACL Status
                    </ion-card-title>
                </ion-card-header>
                <ion-card-content>
                    <ion-grid v-if="aclInfo">
                        <ion-row>
                            <ion-col size="6" size-md="3">
                                <div class="stat-item">
                                    <h2>{{ aclInfo.total_users }}</h2>
                                    <p>Total Users</p>
                                </div>
                            </ion-col>
                            <ion-col size="6" size-md="3">
                                <div class="stat-item">
                                    <h2>{{ aclInfo.total_roles }}</h2>
                                    <p>Total Roles</p>
                                </div>
                            </ion-col>
                            <ion-col size="6" size-md="3">
                                <div class="stat-item">
                                    <h2>{{ aclInfo.default_policy }}</h2>
                                    <p>Default Policy</p>
                                </div>
                            </ion-col>
                            <ion-col size="6" size-md="3">
                                <div class="stat-item">
                                    <h2>{{ aclInfo.version }}</h2>
                                    <p>Version</p>
                                </div>
                            </ion-col>
                        </ion-row>
                    </ion-grid>
                    <div class="acl-actions">
                        <ion-button @click="reloadACL" fill="outline">
                            <ion-icon :icon="refreshOutline" slot="start"></ion-icon>
                            Reload ACL
                        </ion-button>
                        <ion-button @click="viewActiveSessions" fill="outline">
                            <ion-icon :icon="peopleOutline" slot="start"></ion-icon>
                            Active Sessions
                        </ion-button>
                    </div>
                </ion-card-content>
            </ion-card>

            <!-- Tabs for Users and Roles -->
            <ion-segment v-model="activeTab" @ion-change="onSegmentChange">
                <ion-segment-button value="users">
                    <ion-label>Users</ion-label>
                </ion-segment-button>
                <ion-segment-button value="roles">
                    <ion-label>Roles</ion-label>
                </ion-segment-button>
                <ion-segment-button value="permissions">
                    <ion-label>Permission Checker</ion-label>
                </ion-segment-button>
            </ion-segment>

            <!-- Users Tab -->
            <div v-show="activeTab === 'users'">
                <!-- Create User Card -->
                <ion-card>
                    <ion-card-header>
                        <ion-card-title>Create New User</ion-card-title>
                    </ion-card-header>
                    <ion-card-content>
                        <ion-grid>
                            <ion-row>
                                <ion-col size="12" size-md="6">
                                    <ion-item>
                                        <ion-input v-model="newUser.userId" label="User ID" placeholder="Enter user ID"
                                            label-placement="stacked"></ion-input>
                                    </ion-item>
                                </ion-col>
                                <ion-col size="12" size-md="6">
                                    <ion-item>
                                        <ion-select v-model="newUser.roles" multiple label="Roles"
                                            placeholder="Select roles" label-placement="stacked">
                                            <ion-select-option v-for="role in availableRoles" :key="role" :value="role">
                                                {{ role }}
                                            </ion-select-option>
                                        </ion-select>
                                    </ion-item>
                                </ion-col>
                            </ion-row>
                        </ion-grid>
                        <ion-button expand="block" @click="createUser" :disabled="!isValidNewUser"
                            class="ion-margin-top">
                            <ion-icon :icon="personAddOutline" slot="start"></ion-icon>
                            Create User
                        </ion-button>
                    </ion-card-content>
                </ion-card>

                <!-- Users List -->
                <ion-card>
                    <ion-card-header>
                        <ion-card-title>Users ({{ users.length }})</ion-card-title>
                    </ion-card-header>
                    <ion-card-content>
                        <ion-searchbar v-model="userSearchTerm" placeholder="Search users..."
                            @ion-input="filterUsers"></ion-searchbar>

                        <ion-list>
                            <ion-item v-for="user in filteredUsers" :key="user.user_id">
                                <ion-label>
                                    <h2>{{ user.user_id }}</h2>
                                    <p>
                                        <ion-chip v-for="role in user.roles" :key="role" color="primary" size="small">
                                            {{ role }}
                                        </ion-chip>
                                    </p>
                                    <p class="user-permissions">{{ user.all_permissions?.length || 0 }} permission(s)
                                    </p>
                                </ion-label>
                                <ion-button slot="end" fill="clear" @click="editUser(user)">
                                    <ion-icon :icon="createOutline"></ion-icon>
                                </ion-button>
                                <ion-button slot="end" fill="clear" @click="viewUserDetails(user)">
                                    <ion-icon :icon="eyeOutline"></ion-icon>
                                </ion-button>
                                <ion-button slot="end" fill="clear" color="danger" @click="deleteUser(user.user_id)">
                                    <ion-icon :icon="trashOutline"></ion-icon>
                                </ion-button>
                            </ion-item>
                        </ion-list>
                    </ion-card-content>
                </ion-card>
            </div>

            <!-- Roles Tab -->
            <div v-show="activeTab === 'roles'">
                <ion-card>
                    <ion-card-header>
                        <ion-card-title>Available Roles</ion-card-title>
                    </ion-card-header>
                    <ion-card-content>
                        <ion-list>
                            <ion-item v-for="(roleData, roleName) in rolesData" :key="roleName" class="role-item">
                                <ion-label>
                                    <h2>{{ roleName }}</h2>
                                    <p>{{ roleData.description }}</p>
                                    <div class="role-permissions">
                                        <h4>Permissions:</h4>
                                        <div v-for="(perm, idx) in roleData.permissions" :key="idx"
                                            class="permission-item">
                                            <strong>{{ perm.pattern }}</strong>
                                            <div class="permission-actions">
                                                <ion-chip v-for="action in perm.allow" :key="action" color="success"
                                                    size="small">
                                                    ✓ {{ action }}
                                                </ion-chip>
                                                <ion-chip v-for="action in (perm.deny || [])" :key="action"
                                                    color="danger" size="small">
                                                    ✗ {{ action }}
                                                </ion-chip>
                                            </div>
                                        </div>
                                    </div>
                                </ion-label>
                            </ion-item>
                        </ion-list>
                    </ion-card-content>
                </ion-card>
            </div>

            <!-- Permission Checker Tab -->
            <div v-show="activeTab === 'permissions'">
                <ion-card>
                    <ion-card-header>
                        <ion-card-title>Permission Checker</ion-card-title>
                    </ion-card-header>
                    <ion-card-content>
                        <ion-grid>
                            <ion-row>
                                <ion-col size="12" size-md="4">
                                    <ion-item>
                                        <ion-select v-model="permCheck.userId" label="User" placeholder="Select user"
                                            label-placement="stacked">
                                            <ion-select-option v-for="user in users" :key="user.user_id"
                                                :value="user.user_id">
                                                {{ user.user_id }}
                                            </ion-select-option>
                                        </ion-select>
                                    </ion-item>
                                </ion-col>
                                <ion-col size="12" size-md="4">
                                    <ion-item>
                                        <ion-input v-model="permCheck.topic" label="Topic"
                                            placeholder="e.g., sf/sensors/temperature"
                                            label-placement="stacked"></ion-input>
                                    </ion-item>
                                </ion-col>
                                <ion-col size="12" size-md="4">
                                    <ion-item>
                                        <ion-select v-model="permCheck.action" label="Action" label-placement="stacked">
                                            <ion-select-option value="subscribe">Subscribe</ion-select-option>
                                            <ion-select-option value="publish">Publish</ion-select-option>
                                        </ion-select>
                                    </ion-item>
                                </ion-col>
                            </ion-row>
                        </ion-grid>

                        <ion-button expand="block" @click="checkPermission" :disabled="!isValidPermCheck"
                            class="ion-margin-top">
                            <ion-icon :icon="checkmarkCircleOutline" slot="start"></ion-icon>
                            Check Permission
                        </ion-button>

                        <div v-if="permCheckResult" class="permission-result ion-margin-top">
                            <ion-card :color="permCheckResult.allowed ? 'success' : 'danger'">
                                <ion-card-content>
                                    <div class="result-header">
                                        <ion-icon
                                            :icon="permCheckResult.allowed ? checkmarkCircleOutline : closeCircleOutline"></ion-icon>
                                        <h3>{{ permCheckResult.allowed ? 'ALLOWED' : 'DENIED' }}</h3>
                                    </div>
                                    <p><strong>User:</strong> {{ permCheckResult.user_id }}</p>
                                    <p><strong>Topic:</strong> {{ permCheckResult.topic }}</p>
                                    <p><strong>Action:</strong> {{ permCheckResult.action }}</p>
                                </ion-card-content>
                            </ion-card>
                        </div>
                    </ion-card-content>
                </ion-card>
            </div>

            <!-- Edit User Modal -->
            <ion-modal :is-open="showEditModal" @will-dismiss="showEditModal = false">
                <ion-header>
                    <ion-toolbar>
                        <ion-title>Edit User: {{ editingUser?.user_id }}</ion-title>
                        <ion-buttons slot="end">
                            <ion-button @click="showEditModal = false">
                                <ion-icon :icon="closeOutline"></ion-icon>
                            </ion-button>
                        </ion-buttons>
                    </ion-toolbar>
                </ion-header>
                <ion-content class="ion-padding">
                    <ion-list v-if="editingUser">
                        <ion-item>
                            <ion-select v-model="editingUser.roles" multiple label="Roles" placeholder="Select roles"
                                label-placement="stacked">
                                <ion-select-option v-for="role in availableRoles" :key="role" :value="role">
                                    {{ role }}
                                </ion-select-option>
                            </ion-select>
                        </ion-item>
                    </ion-list>
                    <ion-button expand="block" @click="updateUser" class="ion-margin-top">
                        <ion-icon :icon="saveOutline" slot="start"></ion-icon>
                        Update User
                    </ion-button>
                </ion-content>
            </ion-modal>

            <!-- User Details Modal -->
            <ion-modal :is-open="showDetailsModal" @will-dismiss="showDetailsModal = false">
                <ion-header>
                    <ion-toolbar>
                        <ion-title>User Details: {{ selectedUser?.user_id }}</ion-title>
                        <ion-buttons slot="end">
                            <ion-button @click="showDetailsModal = false">
                                <ion-icon :icon="closeOutline"></ion-icon>
                            </ion-button>
                        </ion-buttons>
                    </ion-toolbar>
                </ion-header>
                <ion-content class="ion-padding">
                    <div v-if="selectedUser">
                        <ion-card>
                            <ion-card-header>
                                <ion-card-title>Basic Information</ion-card-title>
                            </ion-card-header>
                            <ion-card-content>
                                <p><strong>User ID:</strong> {{ selectedUser.user_id }}</p>
                                <p><strong>Roles:</strong></p>
                                <div class="roles-list">
                                    <ion-chip v-for="role in selectedUser.roles" :key="role" color="primary">
                                        {{ role }}
                                    </ion-chip>
                                </div>
                            </ion-card-content>
                        </ion-card>

                        <ion-card>
                            <ion-card-header>
                                <ion-card-title>Permissions ({{ selectedUser.permissions.length }})</ion-card-title>
                            </ion-card-header>
                            <ion-card-content>
                                <div v-for="(perm, idx) in selectedUser.permissions" :key="idx"
                                    class="permission-detail">
                                    <h4>{{ perm.pattern }}</h4>
                                    <div class="permission-actions">
                                        <ion-chip v-for="action in perm.allow" :key="action" color="success"
                                            size="small">
                                            ✓ {{ action }}
                                        </ion-chip>
                                        <ion-chip v-for="action in (perm.deny || [])" :key="action" color="danger"
                                            size="small">
                                            ✗ {{ action }}
                                        </ion-chip>
                                    </div>
                                </div>
                            </ion-card-content>
                        </ion-card>
                    </div>
                </ion-content>
            </ion-modal>

            <!-- Active Sessions Modal -->
            <ion-modal :is-open="showSessionsModal" @will-dismiss="showSessionsModal = false">
                <ion-header>
                    <ion-toolbar>
                        <ion-title>Active MQTT Sessions</ion-title>
                        <ion-buttons slot="end">
                            <ion-button @click="showSessionsModal = false">
                                <ion-icon :icon="closeOutline"></ion-icon>
                            </ion-button>
                        </ion-buttons>
                    </ion-toolbar>
                </ion-header>
                <ion-content class="ion-padding">
                    <ion-list>
                        <ion-item v-for="session in activeSessions" :key="session.user_id">
                            <ion-label>
                                <h2>{{ session.user_id }}</h2>
                                <p>
                                    <ion-chip :color="session.is_connected ? 'success' : 'danger'" size="small">
                                        {{ session.is_connected ? 'Connected' : 'Disconnected' }}
                                    </ion-chip>
                                </p>
                                <p>Topics: {{ session.subscribed_topics.length }}</p>
                                <p>Roles: {{ session.roles.join(', ') || 'None' }}</p>
                                <p>Permissions: {{ session.permissions_count }}</p>
                            </ion-label>
                        </ion-item>
                    </ion-list>
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
    IonGrid, IonRow, IonCol, IonItem, IonLabel, IonInput, IonSelect, IonSelectOption,
    IonChip, IonList, IonSearchbar, IonSegment, IonSegmentButton, IonModal,
    IonTextarea, alertController, toastController
} from '@ionic/vue';

import {
    refreshOutline, shieldCheckmarkOutline, peopleOutline, personAddOutline,
    createOutline, eyeOutline, trashOutline, checkmarkCircleOutline,
    closeCircleOutline, closeOutline, saveOutline
} from 'ionicons/icons';

import apiService from '@/services/api';

// State
const isLoading = ref(false);
const activeTab = ref('users');

// Data
const aclInfo = ref(null);
const users = ref([]);
const rolesData = ref({});
const availableRoles = ref([]);
const activeSessions = ref([]);

// Search and filtering
const userSearchTerm = ref('');
const filteredUsers = ref([]);

// Modals
const showEditModal = ref(false);
const showDetailsModal = ref(false);
const showSessionsModal = ref(false);

// Forms
const newUser = ref({
    userId: '',
    roles: []
});

const editingUser = ref(null);
const selectedUser = ref(null);

const permCheck = ref({
    userId: '',
    topic: '',
    action: 'subscribe'
});

const permCheckResult = ref(null);

// Computed
const isValidNewUser = computed(() => {
    return newUser.value.userId.trim() && newUser.value.roles.length > 0;
});

const isValidPermCheck = computed(() => {
    return permCheck.value.userId && permCheck.value.topic && permCheck.value.action;
});

// Methods
const showToast = async (message, color = 'primary') => {
    const toast = await toastController.create({
        message,
        duration: 3000,
        color,
        position: 'bottom'
    });
    await toast.present();
};

const showAlert = async (header, message) => {
    const alert = await alertController.create({
        header,
        message,
        buttons: ['OK']
    });
    await alert.present();
};

// Data loading methods
const loadACLInfo = async () => {
    try {
        const response = await apiService.getACLInfo();
        aclInfo.value = response.data;
    } catch (err) {
        console.error('Failed to load ACL info:', err);
        showToast('Failed to load ACL info', 'danger');
    }
};

const loadUsers = async () => {
    try {
        const response = await apiService.getAllUsers();
        users.value = response.data || [];
        filteredUsers.value = users.value;
        console.log(users.value)
    } catch (err) {
        console.error('Failed to load users:', err);
        showToast('Failed to load users', 'danger');
    }
};

const loadRoles = async () => {
    try {
        const response = await apiService.getAllRoles();
        rolesData.value = response.data || {};
        availableRoles.value = Object.keys(rolesData.value);
    } catch (err) {
        console.error('Failed to load roles:', err);
        showToast('Failed to load roles', 'danger');
    }
};

const loadActiveSessions = async () => {
    try {
        const response = await apiService.getActiveSessions();
        activeSessions.value = response.data || [];
    } catch (err) {
        console.error('Failed to load active sessions:', err);
        showToast('Failed to load active sessions', 'danger');
    }
};

const refreshData = async () => {
    isLoading.value = true;
    try {
        await Promise.all([
            loadACLInfo(),
            loadUsers(),
            loadRoles(),
            loadActiveSessions()
        ]);
        showToast('Data refreshed', 'success');
    } catch (err) {
        showToast('Failed to refresh data', 'danger');
    } finally {
        isLoading.value = false;
    }
};

// User management methods
const createUser = async () => {
    try {
        await apiService.createUser({
            user_id: newUser.value.userId,
            roles: newUser.value.roles,
            custom_permissions: []
        });

        newUser.value = { userId: '', roles: [] };
        await loadUsers();
        await loadACLInfo();
        showToast('User created successfully', 'success');
    } catch (err) {
        showToast('Failed to create user', 'danger');
    }
};

const editUser = (user) => {
    editingUser.value = { ...user };
    showEditModal.value = true;
};

const updateUser = async () => {
    try {
        await apiService.updateUser(editingUser.value.user_id, {
            roles: editingUser.value.roles
        });

        showEditModal.value = false;
        editingUser.value = null;
        await loadUsers();
        showToast('User updated successfully', 'success');
    } catch (err) {
        showToast('Failed to update user', 'danger');
    }
};

const deleteUser = async (userId) => {
    const alert = await alertController.create({
        header: 'Delete User',
        message: `Are you sure you want to delete user "${userId}"?`,
        buttons: [
            { text: 'Cancel', role: 'cancel' },
            {
                text: 'Delete',
                role: 'destructive',
                handler: async () => {
                    try {
                        await apiService.deleteUser(userId);
                        await loadUsers();
                        await loadACLInfo();
                        showToast('User deleted successfully', 'success');
                    } catch (err) {
                        showToast('Failed to delete user', 'danger');
                    }
                }
            }
        ]
    });
    await alert.present();
};

const viewUserDetails = (user) => {
    selectedUser.value = user;
    showDetailsModal.value = true;
};

// Permission checking
const checkPermission = async () => {
    try {
        permCheckResult.value = await apiService.checkPermission(
            {
                user_id: permCheck.value.userId,
                topic: permCheck.value.topic,
                action: permCheck.value.action
            }
        );
    } catch (err) {
        showToast('Failed to check permission', 'danger');
    }
};

// Utility methods
const filterUsers = () => {
    const term = userSearchTerm.value.toLowerCase();
    if (term) {
        filteredUsers.value = users.value.filter(user =>
            user.user_id.toLowerCase().includes(term) ||
            user.roles.some(role => role.toLowerCase().includes(term))
        );
    } else {
        filteredUsers.value = users.value;
    }
};

const onSegmentChange = (event) => {
    activeTab.value = event.detail.value;
    permCheckResult.value = null; // Reset permission check result when switching tabs
};

const reloadACL = async () => {
    try {
        await apiService.reloadACL();
        await refreshData();
        showToast('ACL configuration reloaded', 'success');
    } catch (err) {
        showToast('Failed to reload ACL', 'danger');
    }
};

const viewActiveSessions = async () => {
    await loadActiveSessions();
    showSessionsModal.value = true;
};

// Lifecycle
onMounted(() => {
    refreshData();
});
</script>

<style scoped>
.stat-item {
    text-align: center;
    padding: 16px;
}

.stat-item h2 {
    margin: 0;
    font-size: 2rem;
    font-weight: bold;
    color: var(--ion-color-primary);
}

.stat-item p {
    margin: 8px 0 0 0;
    font-size: 0.8rem;
    color: var(--ion-color-medium);
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.acl-actions {
    display: flex;
    gap: 8px;
    margin-top: 16px;
}

.user-permissions {
    font-size: 0.8rem;
    color: var(--ion-color-medium);
    margin-top: 4px;
}

.role-item {
    margin-bottom: 16px;
}

.role-permissions {
    margin-top: 12px;
}

.role-permissions h4 {
    margin: 0 0 8px 0;
    font-size: 0.9rem;
    color: var(--ion-color-medium);
}

.permission-item {
    margin-bottom: 8px;
    padding: 8px;
    background: var(--ion-color-light);
    border-radius: 4px;
}

.permission-item strong {
    display: block;
    margin-bottom: 4px;
    font-family: monospace;
    font-size: 0.85rem;
}

.permission-actions {
    display: flex;
    gap: 4px;
    flex-wrap: wrap;
}

.permission-result .result-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 12px;
}

.permission-result h3 {
    margin: 0;
    font-size: 1.2rem;
}

.roles-list {
    margin-top: 8px;
}

.permission-detail {
    margin-bottom: 16px;
    padding: 12px;
    background: var(--ion-color-light);
    border-radius: 8px;
}

.permission-detail h4 {
    margin: 0 0 8px 0;
    font-family: monospace;
    font-size: 0.9rem;
}

@media (max-width: 768px) {
    .acl-actions {
        flex-direction: column;
    }

    .permission-actions {
        justify-content: flex-start;
    }

    .stat-item h2 {
        font-size: 1.5rem;
    }
}
</style>