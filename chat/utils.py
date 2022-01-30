import settings
import asyncio


async def clean_chat(app):
    while True:
        await asyncio.sleep(10)
        print('Chat clener working')
        for group_id,group_info in app['chat'].items():
            remove_elems = len(group_info['events'])-settings.MAX_MESSAGE_TO_STORE
            for i in range(remove_elems):
                item = app['chat'][group_id]['events'].pop(0)
                print(f'Event {item} was deleted in grope{group_id}')
