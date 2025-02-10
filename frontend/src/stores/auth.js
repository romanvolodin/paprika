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
    },
  },
});
