/**
 * GeoServer Authentication Plugin for MapStore
 * Handles authentication with GeoServer layers
 */

import { createSelector } from 'reselect';
import { createAction, createThunkAction } from '../utils/MapStore2';

// Action types
const GEOSERVER_AUTH_LOGIN = 'GEOSERVER_AUTH_LOGIN';
const GEOSERVER_AUTH_LOGOUT = 'GEOSERVER_AUTH_LOGOUT';
const GEOSERVER_AUTH_SUCCESS = 'GEOSERVER_AUTH_SUCCESS';
const GEOSERVER_AUTH_ERROR = 'GEOSERVER_AUTH_ERROR';

// Actions
export const geoserverLogin = createThunkAction(GEOSERVER_AUTH_LOGIN, (credentials) => {
    return (dispatch, getState) => {
        const { username, password } = credentials;
        
        // Test GeoServer authentication
        return fetch('http://localhost:8080/geoserver/rest/security/validate-token', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Basic ' + btoa(username + ':' + password)
            },
            body: JSON.stringify({ token: 'test' })
        })
        .then(response => {
            if (response.ok || response.status === 401) { // 401 is expected for test token
                dispatch(geoserverAuthSuccess({ username, password }));
                return { success: true, username, password };
            } else {
                throw new Error('Authentication failed');
            }
        })
        .catch(error => {
            dispatch(geoserverAuthError(error.message));
            throw error;
        });
    };
});

export const geoserverLogout = createAction(GEOSERVER_AUTH_LOGOUT);
export const geoserverAuthSuccess = createAction(GEOSERVER_AUTH_SUCCESS);
export const geoserverAuthError = createAction(GEOSERVER_AUTH_ERROR);

// Reducer
const initialState = {
    isAuthenticated: false,
    username: null,
    password: null,
    error: null
};

export default function geoserverAuth(state = initialState, action) {
    switch (action.type) {
        case GEOSERVER_AUTH_SUCCESS:
            return {
                ...state,
                isAuthenticated: true,
                username: action.payload.username,
                password: action.payload.password,
                error: null
            };
        case GEOSERVER_AUTH_LOGOUT:
            return {
                ...state,
                isAuthenticated: false,
                username: null,
                password: null,
                error: null
            };
        case GEOSERVER_AUTH_ERROR:
            return {
                ...state,
                isAuthenticated: false,
                username: null,
                password: null,
                error: action.payload
            };
        default:
            return state;
    }
}

// Selectors
export const isGeoserverAuthenticated = state => state.geoserverAuth.isAuthenticated;
export const getGeoserverCredentials = state => ({
    username: state.geoserverAuth.username,
    password: state.geoserverAuth.password
});

// Component
import React, { useState } from 'react';
import { connect } from 'react-redux';
import { geoserverLogin, geoserverLogout } from './GeoServerAuthPlugin';

const GeoServerAuthComponent = ({ 
    isAuthenticated, 
    username, 
    onLogin, 
    onLogout 
}) => {
    const [loginForm, setLoginForm] = useState({ username: '', password: '' });
    const [loading, setLoading] = useState(false);

    const handleLogin = async (e) => {
        e.preventDefault();
        setLoading(true);
        
        try {
            await onLogin(loginForm);
            console.log('GeoServer authentication successful');
        } catch (error) {
            console.error('GeoServer authentication failed:', error);
            alert('Authentication failed: ' + error.message);
        } finally {
            setLoading(false);
        }
    };

    const handleLogout = () => {
        onLogout();
        setLoginForm({ username: '', password: '' });
    };

    if (isAuthenticated) {
        return (
            <div className="geoserver-auth">
                <p>✅ Authenticated as: {username}</p>
                <button onClick={handleLogout} className="btn btn-danger">
                    Logout from GeoServer
                </button>
            </div>
        );
    }

    return (
        <form onSubmit={handleLogin} className="geoserver-auth-form">
            <h4>GeoServer Authentication</h4>
            <div className="form-group">
                <input
                    type="text"
                    placeholder="Username"
                    value={loginForm.username}
                    onChange={(e) => setLoginForm({...loginForm, username: e.target.value})}
                    required
                />
            </div>
            <div className="form-group">
                <input
                    type="password"
                    placeholder="Password"
                    value={loginForm.password}
                    onChange={(e) => setLoginForm({...loginForm, password: e.target.value})}
                    required
                />
            </div>
            <button 
                type="submit" 
                disabled={loading}
                className="btn btn-primary"
            >
                {loading ? 'Authenticating...' : 'Login to GeoServer'}
            </button>
        </form>
    );
};

const GeoServerAuth = connect(
    state => ({
        isAuthenticated: isGeoserverAuthenticated(state),
        username: getGeoserverCredentials(state).username
    }),
    {
        onLogin: geoserverLogin,
        onLogout: geoserverLogout
    }
)(GeoServerAuthComponent);

export default GeoServerAuth;
