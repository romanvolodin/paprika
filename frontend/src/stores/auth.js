import { defineStore } from 'pinia';

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    isUserAuthenticated: false,
  }),
  actions: {
    setUser(user) {
      this.user = user;
      this.isUserAuthenticated = true
      localStorage.setItem('auth', JSON.stringify({ user, isUserAuthenticated: true }))
    },
    initializeAuthState() {
      const savedAuth = localStorage.getItem('auth');
      if (savedAuth) {
        const { user, isUserAuthenticated } = JSON.parse(savedAuth)
        this.user = user
        this.isUserAuthenticated = isUserAuthenticated
      }
    },
  },
});
