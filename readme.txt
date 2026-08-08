Abraham Rodriguez VAZQUEZ

Los valores del dataset constan de las mediciones de sensores de 10 samples anteriores asi como el estado mismo
en posicion y cuaternion.

names=["imu_accx","imu_accy","imu_accz","imu_wx","imu_wy","imu_wz","imu_magx","imu_magy","imu_magz",
       "gps_velx","gps_vely","gps_velz",
       "prev_state_posx","prev_state_posy","prev_state_posz",
       "prev_state_quatw","prev_state_quatx","prev_state_quaty","prev_state_quatz",
       "gt_state_posx","gt_state_posy","gt_state_posz",
       "gt_state_quatw","gt_state_quatx","gt_state_quaty","gt_state_quatz",]


Dataset generado con ayuda de los generadores gpsSensor e IMUSensor de MATLAB
https://la.mathworks.com/help/nav/ref/imusensor-system-object.html
https://la.mathworks.com/help/nav/ref/gpssensor-system-object.html