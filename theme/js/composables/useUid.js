let uid = 0;
export default function useUid(id = 'id') {
    uid++;
    return {
        id: `${id}-${uid}`,
    };
}