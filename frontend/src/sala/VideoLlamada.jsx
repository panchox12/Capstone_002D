import { LiveKitRoom, VideoConference } from '@livekit/components-react'
import '@livekit/components-styles'

/**
 * La llamada en si: video, audio, chat y pantalla compartida los pone LiveKit.
 * Esta en su propio archivo para que las pruebas lo reemplacen sin cargar WebRTC.
 */
export function VideoLlamada({ permiso, alSalir }) {
  return (
    <div data-lk-theme="default" className="h-[70vh] overflow-hidden rounded-tarjeta">
      <LiveKitRoom serverUrl={permiso.url} token={permiso.token} connect video audio onDisconnected={alSalir}>
        <VideoConference />
      </LiveKitRoom>
    </div>
  )
}