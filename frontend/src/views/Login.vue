<template>
    <ion-page>
        <ion-content class="ion-padding login-content">
            <div class="login-container">
                <!-- Logo / Title -->
                <div class="login-header">
                    <ion-icon :icon="businessOutline" class="logo-icon" />
                    <h1>Smart Factory</h1>
                    <p>Sign in to your account</p>
                </div>

                <!-- Login Form -->
                <ion-card class="login-card">
                    <ion-card-content>
                        <form @submit.prevent="handleLogin">
                            <ion-item lines="full" class="form-item">
                                <ion-label position="floating">Username</ion-label>
                                <ion-input v-model="username" type="text" autocomplete="username" required
                                    :disabled="isLoading" />
                            </ion-item>

                            <ion-item lines="full" class="form-item">
                                <ion-label position="floating">Password</ion-label>
                                <ion-input v-model="password" :type="showPassword ? 'text' : 'password'"
                                    autocomplete="current-password" required :disabled="isLoading" />
                                <ion-button slot="end" fill="clear" @click="showPassword = !showPassword" tabindex="-1">
                                    <ion-icon :icon="showPassword ? eyeOffOutline : eyeOutline" />
                                </ion-button>
                            </ion-item>

                            <!-- Error message -->
                            <div v-if="errorMessage" class="error-message">
                                <ion-icon :icon="alertCircleOutline" />
                                {{ errorMessage }}
                            </div>

                            <ion-button expand="block" type="submit" class="login-button" :disabled="isLoading">
                                <ion-spinner v-if="isLoading" name="crescent" />
                                <span v-else>Sign In</span>
                            </ion-button>
                        </form>
                    </ion-card-content>
                </ion-card>

                <!-- Register link -->
                <div class="register-link">
                    <span>Don't have an account?</span>
                    <ion-button fill="clear" router-link="/register" size="small">
                        Create Account
                    </ion-button>
                </div>
            </div>
        </ion-content>
    </ion-page>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import {
    IonPage, IonContent, IonCard, IonCardContent,
    IonItem, IonLabel, IonInput, IonButton, IonIcon, IonSpinner
} from '@ionic/vue'
import {
    businessOutline, eyeOutline, eyeOffOutline, alertCircleOutline
} from 'ionicons/icons'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const username = ref('')
const password = ref('')
const showPassword = ref(false)
const isLoading = ref(false)
const errorMessage = ref('')

const handleLogin = async () => {
    if (!username.value || !password.value) {
        errorMessage.value = 'Please enter your username and password.'
        return
    }

    isLoading.value = true
    errorMessage.value = ''

    try {
        await authStore.login(username.value, password.value)
        router.replace('/dashboard')
    } catch (error) {
        const status = error.response?.status
        if (status === 401) {
            errorMessage.value = 'Incorrect username or password.'
        } else if (status === 503) {
            errorMessage.value = 'Service unavailable. Please try again later.'
        } else {
            errorMessage.value = 'Login failed. Please try again.'
        }
    } finally {
        isLoading.value = false
    }
}
</script>

<style scoped>
.login-content {
    --background: var(--ion-color-light);
}

.login-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 100%;
    padding: 24px 16px;
}

.login-header {
    text-align: center;
    margin-bottom: 32px;
}

.logo-icon {
    font-size: 64px;
    color: var(--ion-color-primary);
    margin-bottom: 12px;
}

.login-header h1 {
    font-size: 28px;
    font-weight: 700;
    color: var(--ion-color-dark);
    margin: 0 0 8px;
}

.login-header p {
    color: var(--ion-color-medium);
    margin: 0;
}

.login-card {
    width: 100%;
    max-width: 420px;
    border-radius: 16px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.form-item {
    margin-bottom: 8px;
    --border-radius: 8px;
}

.error-message {
    display: flex;
    align-items: center;
    gap: 6px;
    color: var(--ion-color-danger);
    font-size: 14px;
    padding: 8px 16px;
    margin-top: 8px;
}

.login-button {
    margin-top: 24px;
    --border-radius: 8px;
    height: 48px;
    font-size: 16px;
    font-weight: 600;
}

.register-link {
    display: flex;
    align-items: center;
    margin-top: 20px;
    color: var(--ion-color-medium);
    font-size: 14px;
}
</style>