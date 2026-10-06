import { apiService } from './apiService';

// Thin feature service (fams-ui-standards §3.3): URL + params only.
export const AuthService = {
  /** Legacy $signIn: POST FAMSlegacy/Authenticate -> data.value[0].token */
  authenticate(username, password) {
    return apiService.postAnonymous('FAMSlegacy/Authenticate', { Username: username, Password: password });
  },
  getPermissions() {
    return apiService.get('Role/GetPermissions');
  }
};
