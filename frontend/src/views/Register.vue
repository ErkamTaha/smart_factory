<template>
    <ion-page>
        <ion-content class="ion-padding register-content">
            <div class="register-container">
                <!-- Logo / Title -->
                <div class="register-header">
                    <ion-icon :icon="businessOutline" class="logo-icon" />
                    <h1>Smart Factory</h1>
                    <p>Create your account</p>
                </div>

                <!-- Register Form -->
                <ion-card class="register-card">
                    <ion-card-content>
                        <form @submit.prevent="handleRegister">
                            <ion-item lines="full" class="form-item">
                                <ion-label position="floating">Username</ion-label>
                                <ion-input v-model="username" type="text" autocomplete="username" required
                                    :disabled="isLoading" />
                            </ion-item>

                            <ion-item lines="full" class="form-item">
                                <ion-label position="floating">Email</ion-label>
                                <ion-input v-model="email" type="email" autocomplete="email" required
                                    :disabled="isLoading" />
                            </ion-item>

                            <ion-item lines="full" class="form-item password-item">
                                <ion-label position="floating">Password</ion-label>
                                <ion-input v-model="password" :type="showPassword ? 'text' : 'password'"
                                    autocomplete="new-password" required :disabled="isLoading" />
                                <ion-button slot="end" fill="clear" class="eye-btn" @click="showPassword = !showPassword" tabindex="-1">
                                    <ion-icon :icon="showPassword ? eyeOffOutline : eyeOutline" />
                                </ion-button>
                            </ion-item>

                            <ion-item lines="full" class="form-item">
                                <ion-label position="floating">Confirm Password</ion-label>
                                <ion-input v-model="confirmPassword" :type="showPassword ? 'text' : 'password'"
                                    autocomplete="new-password" required :disabled="isLoading" />
                            </ion-item>

                            <!-- Error message -->
                            <div v-if="errorMessage" class="error-message">
                                <ion-icon :icon="alertCircleOutline" />
                                {{ errorMessage }}
                            </div>

                            <!-- Success message -->
                            <div v-if="successMessage" class="success-message">
                                <ion-icon :icon="checkmarkCircleOutline" />
                                {{ successMessage }}
                            </div>

                            <ion-button expand="block" type="submit" class="register-button" :disabled="isLoading">
                                <ion-spinner v-if="isLoading" name="crescent" />
                                <span v-else>Create Account</span>
                            </ion-button>
                        </form>
                    </ion-card-content>
                </ion-card>

                <!-- Login link -->
                <div class="login-link">
                    <span>Already have an account?</span>
                    <ion-button fill="clear" router-link="/login" size="small">
                        Sign In
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
    businessOutline, eyeOutline, eyeOffOutline,
    alertCircleOutline, checkmarkCircleOutline
} from 'ionicons/icons'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const username = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const showPassword = ref(false)
const isLoading = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

const handleRegister = async () => {
    errorMessage.value = ''
    successMessage.value = ''

    if (!username.value || !email.value || !password.value) {
        errorMessage.value = 'Please fill in all fields.'
        return
    }

    if (password.value !== confirmPassword.value) {
        errorMessage.value = 'Passwords do not match.'
        return
    }

    if (password.value.length < 6) {
        errorMessage.value = 'Password must be at least 6 characters.'
        return
    }

    isLoading.value = true

    try {
        await authStore.register(username.value, email.value, password.value)
        successMessage.value = 'Account created! Signing you in...'

        // Auto-login after registration
        await authStore.login(username.value, password.value)
        router.replace('/dashboard')
    } catch (error) {
        const status = error.response?.status
        const detail = error.response?.data?.detail

        if (status === 400 && typeof detail === 'string') {
            errorMessage.value = detail
        } else if (status === 422) {
            errorMessage.value = 'Invalid input. Check your email format.'
        } else {
            errorMessage.value = 'Registration failed. Please try again.'
        }
    } finally {
        isLoading.value = false
    }
}
</script>

<style scoped>
.register-content {
    --background: var(--ion-color-light);
}

.register-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 100%;
    padding: 24px 16px;
}

.register-header {
    text-align: center;
    margin-bottom: 32px;
}

.logo-icon {
    font-size: 64px;
    color: var(--ion-color-primary);
    margin-bottom: 12px;
}

.register-header h1 {
    font-size: 28px;
    font-weight: 700;
    color: var(--ion-color-dark);
    margin: 0 0 8px;
}

.register-header p {
    color: var(--ion-color-medium);
    margin: 0;
}

.register-card {
    width: 100%;
    max-width: 420px;
    border-radius: 16px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.form-item {
    margin-bottom: 8px;
}

.password-item {
    --inner-padding-end: 0;
}

.eye-btn {
    align-self: flex-end;
    margin-bottom: 6px;
    height: 36px;
    width: 36px;
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

.success-message {
    display: flex;
    align-items: center;
    gap: 6px;
    color: var(--ion-color-success);
    font-size: 14px;
    padding: 8px 16px;
    margin-top: 8px;
}

.register-button {
    margin-top: 24px;
    --border-radius: 8px;
    height: 48px;
    font-size: 16px;
    font-weight: 600;
}

.login-link {
    display: flex;
    align-items: center;
    margin-top: 20px;
    color: var(--ion-color-medium);
    font-size: 14px;
}
</style>