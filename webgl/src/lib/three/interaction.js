import * as THREE from 'three';
export function attachBoardInteraction(canvas, camera, target, onPick) {
    const ray = new THREE.Raycaster();
    const mouse = new THREE.Vector2();
    const onMove = (event) => {
        const rect = canvas.getBoundingClientRect();
        mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
        ray.setFromCamera(mouse, camera);
        const hits = ray.intersectObject(target, true);
        if (!hits.length) {
            onPick(null);
            return;
        }
        const p = hits[0].point;
        onPick({ x: Math.floor(p.x), y: Math.floor(p.y), z: Math.floor(p.z) });
    };
    canvas.addEventListener('pointermove', onMove);
    return () => canvas.removeEventListener('pointermove', onMove);
}
//# sourceMappingURL=interaction.js.map