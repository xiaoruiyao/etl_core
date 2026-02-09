import axios from 'axios'

const api = axios.create({
    baseURL: 'http://localhost:8000/api',
    timeout: 30000,
    headers: {
        'Content-Type': 'application/json'
    }
})

// 请求拦截器
api.interceptors.request.use(
    config => config,
    error => Promise.reject(error)
)

// 响应拦截器
api.interceptors.response.use(
    response => response.data,
    error => {
        console.error('API Error:', error)
        return Promise.reject(error)
    }
)

// ========== Stats API ==========
export const getStats = () => api.get('/stats')

// ========== Results API ==========
export const getResults = (params) => api.get('/results', { params })

export const getResultDetail = (id) => api.get(`/results/${id}`)

export const getResultCurves = (id) => api.get(`/results/${id}/curves`)

export const getResultSteps = (id) => api.get(`/results/${id}/steps`)

// ========== Alarms API ==========
export const getAlarms = (params) => api.get('/alarms', { params })

export const getAlarmHierarchy = (id) => api.get(`/alarms/${id}/hierarchy`)

// ========== Devices API ==========
export const getDevices = (params) => api.get('/devices', { params })

export const getDeviceDetail = (name) => api.get(`/devices/${encodeURIComponent(name)}`)

export const getDeviceResults = (name, params) =>
    api.get(`/devices/${encodeURIComponent(name)}/results`, { params })

export const getDeviceAlarms = (name, params) =>
    api.get(`/devices/${encodeURIComponent(name)}/alarms`, { params })

export const getDeviceUris = (name) =>
    api.get(`/devices/${encodeURIComponent(name)}/uris`)

// ========== Hierarchy & Points API ==========
export const getStructureTree = () => api.get('/structure/tree')

export const getPoints = (params) => api.get('/points', { params })

export default api
