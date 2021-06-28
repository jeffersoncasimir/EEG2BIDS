import React, {useState, useEffect} from 'react';
import PropTypes from 'prop-types';
import '../../css/Authentication.css';

import {
  TextInput,
} from './inputs';

export const AuthenticationMessage = (props) => {
  // React state
  const [loginStatus, setLoginStatus] = useState(false);
  const [loginMessage, setLoginMessage] = useState(
      'You are not logged in to LORIS Account',
  );
  const [loginLink, setLoginLink] = useState(
      'Log in...',
  );

  /**
   * Similar to componentDidMount and componentDidUpdate.
   */
  useEffect(() => {
    const myAPI = window['myAPI'];
    const credentials = myAPI.getLorisAuthenticationCredentials();
    if (credentials) {
      setLoginMessage('LORIS Account set as [todo username]');
      setLoginLink('Sign in to another account..');
    }
  }, []);

  /**
   * User clicked sign in..
   */
  const handleClick = () => {
    props.setAuthCredentialsVisible(true);
    if (loginStatus) {
      // Already logged in.
    } else {
      // Not logged in.
    }
  };
  return (
    <div className='authMessageContainer'>
      <span className='loginMessage'>
        {loginMessage}
      </span>
      <a className='loginLink' onClick={handleClick}>
        &nbsp;&nbsp;&nbsp;&nbsp;{loginLink}
      </a>
    </div>
  );
};
AuthenticationMessage.propTypes = {
  onUserInput: PropTypes.func,
};

export const AuthenticationCredentials = (props) => {
  // React state
  const [lorisURL, setLorisURL] = useState('');
  const [lorisUsername, setLorisUsername] = useState('');
  const [lorisPassword, setLorisPassword] = useState('');
  /**
   * Close the Authentication Credentials
   */
  const handleClose = () => {
    props.close(true);
  };
  /**
   * onUserInput - input change by user.
   * @param {string} name - element name
   * @param {object|string|boolean} value - element value
   */
  const onUserInput = (name, value) => {
    console.log(name);
    switch (name) {
      case 'lorisURL':
        setLorisURL(value);
        break;
      case 'lorisUsername':
        setLorisUsername(value);
        break;
      case 'lorisPassword':
        setLorisPassword(value);
        break;
    }
  };
  const styleVisible = {visibility: props.show ? 'visible' : 'hidden'};
  const styleAnimation = {width: props.width ? props.width : 'auto'};
  const styleContainer = {
    opacity: props.show ? 1 : 0,
    transform: props.show ? 'translateY(0)' : 'translateY(-25%)',
  };
  return (
    <div className='authCredentialsOverlay'
      style={styleVisible}>
      <div className='authCredentialsContainer'
        style={styleVisible}>
        <div className='authCredentialsAnimation'
          style={styleAnimation}>
          <div className='authCredentialsDialog'
            style={styleContainer}>
            <span className='authCredentialsHeader'>
              {props.title}
              <span className='authCredentialsHeaderClose'
                onClick={handleClose}>
                ×
              </span>
            </span>
            <div className='authCredentialsContent'>
              <TextInput id='lorisURL'
                name='lorisURL'
                required={true}
                label='URL of LORIS instance'
                placeholder={'Example: https://loris.ca'}
                value={lorisURL}
                onUserInput={onUserInput}
              />
              <TextInput id='lorisUsername'
                name='lorisUsername'
                required={true}
                label='Username'
                placeholder={'Username'}
                value={lorisUsername}
                onUserInput={onUserInput}
              />
              <TextInput id='lorisPassword'
                name='lorisPassword'
                required={true}
                label='Password'
                placeholder={'Password'}
                value={lorisPassword}
                onUserInput={onUserInput}
              />
              {props.children}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
AuthenticationCredentials.propTypes = {
  show: PropTypes.bool.isRequired,
  close: PropTypes.func.isRequired,
  width: PropTypes.string,
  title: PropTypes.string,
  children: PropTypes.node,
};
AuthenticationCredentials.defaultProps = {
  width: null,
  title: null,
  children: null,
};

export default {
  AuthenticationMessage,
  AuthenticationCredentials,
};
