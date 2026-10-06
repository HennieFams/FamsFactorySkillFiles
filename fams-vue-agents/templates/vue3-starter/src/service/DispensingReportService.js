import { apiService } from './apiService';

// Example thin service. Legacy endpoint from fams-quick-report §4 - but WITHOUT the
// clientKey/accountkey query parameters: apiService sends them as headers.
// Before wiring a real screen to this, check in the legacy view which parameters it
// actually sends. If the API still requires keys in the query string, raise it with
// the Vue Lead - don't add them here silently.
export const DispensingReportService = {
  getLogbook({ fromDate, toDate }, signal) {
    return apiService.get('QuickViewDispensing/Get_Reportinglogbook', {
      params: { fromdate: fromDate, todate: toDate },
      signal
    });
  }
};
