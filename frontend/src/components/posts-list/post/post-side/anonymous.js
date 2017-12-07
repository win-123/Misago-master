/* jshint ignore:start */
import React from 'react';
import Avatar from 'misago/components/avatar';
import UserStatus, { StatusIcon, StatusLabel } from 'misago/components/user-status';
import UserPostcount from './user-postcount';
import UserTitle from './user-title';

export default function({ post }) {
  return (
    <div className="col-xs-12 col-md-3 post-side post-side-anonymous">
      <Select
        post={post}
        thread={thread}
      />
      <Controls
        post={post}
        thread={thread}
      />
      <div className="media">
        <div className="media-left">
          <span>
            <Avatar
              className="poster-avatar"
              size={100}
            />
          </span>
        </div>
        <div className="media-body">

          <span className="media-heading item-title">
            {post.poster_name}
          </span>

          <span className="user-title user-title-anonymous">
            {gettext("Removed user")}
          </span>

        </div>
      </div>
    </div>
  );
}