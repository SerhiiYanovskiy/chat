from aiohttp import web, WSCloseCode
import aiohttp
import logging
import settings

log = logging.getLogger(__name__)


async def send_massege_all(app, group_id, message):
    for elem in app['chat'][group_id]['users'].values():
        await elem.send_json(message)


async def join_group(app, current_ws, group_id, username):
    response = {'action': 'group connection', 'is_success': False,
                     'message': ''}
    if 3 <= len(group_id) <= 8:
        if app['chat'].get(group_id):
            if app['chat'][group_id]['users_count'] < settings.MAX_USERS_IN_GROUP:
                if username in app['chat'][group_id]['users'].keys():
                    response['message'] = 'This nickname is busy'
                else:
                    last_messages = app['chat'][group_id]['events'][-settings.MAX_MESSAGE_TO_STORE:]
                    response['is_success'] = True
                    response['message'] = 'OK'
                    response['chat_history'] = last_messages
                    app['chat'][group_id]['users'][username] = current_ws
                    app['chat'][group_id]['users_count'] += 1
            else:
                response['message'] = f'The numbers of group members has exceeded the limit{settings.MAX_USERS_IN_GROUP}.'
        else:
            app['chat'][group_id] = {'users': {}, 'users_count': 1, 'events': [], 'admin': username}
            app['chat'][group_id]['users'][username] = current_ws
            response['is_success'] = True
            response['message'] = f'Group {group_id} was created.'
    else:
        response['message'] = 'Group name must be (3 to 8 characters'

    return response


async def remove_user(app, current_ws, group_id, current_username, target_username):
    response = {'action': 'remove', 'is_success': False, 'message': ''}
    admin_name = app['chat'][group_id]['admin']
    if current_username!=target_username:
        if admin_name == current_username:
            if target_username in app['chat'][group_id]['users'].keys():
                response['is_success'] = True
                response['message'] = 'OK'
                target_user_ws = app['chat'][group_id]['users'][target_username]
                await target_user_ws.close()
            else:
                response['message'] = 'No user'
        else:
            response['message'] = 'You don`t have rights to remove'
    else:
        response['message'] = 'You can`t remove yourself'
    return response




async def chat(request):
    current = web.WebSocketResponse()
    ready = current.can_prepare(request=request)
    if not ready:
        await current.close(code=WSCloseCode.PROTOCOL_ERROR)
    await current.prepare(request)
    await current.send_json({'action': 'ws connection established'})
    try:
        async for msg in current:
            if msg.type == aiohttp.WSMsgType.TEXT:
                msg_json = msg.json()
                action = msg_json.get('action')
                if action == 'connect':
                    group_id, current_username = msg_json.get('group'), msg_json.get('username')
                    response = await join_group(request.app, current, group_id, current_username)
                    await current.send_json(response)
                    if response['is_success']:
                        message = {'action': 'new join', 'group': group_id, 'name': current_username}
                        await send_massege_all(request.app, group_id, message)
                elif action == 'message':
                    text = msg_json.get('text')
                    message = {'action': 'message', 'username': current_username, 'text': text}
                    request.app['chat'][group_id]['events'].append(message)
                    await send_massege_all(request.app, group_id, message)
                elif action == 'kick':
                    target_username = msg_json.get('target_user')
                    response = await remove_user(request.app, current, group_id, current_username, target_username)
                    await current.send_json(response)
                elif action == 'disconnect':
                    await current.send_json(
                        {'action': 'disconnect', 'is_success': True, 'message': 'You were disconnected'})
                    break;
                else:
                    await current.send_json(
                        {'action': action, 'is_success': False, 'message': 'Unknown command'})
    finally:
        if request.app['chat'][group_id]['users_count'] > 1:
            del request.app['chat'][group_id]['users'][current_username]
            request.app['chat'][group_id]['users_count'] -= 1
            message = {'action': 'disconnect', 'room': group_id, 'username': current_username}
            await send_massege_all(request.app, group_id, message)
        else:
            del request.app['chat'][group_id]
            log.info(f'Group {group_id} was deleted!')
    return current