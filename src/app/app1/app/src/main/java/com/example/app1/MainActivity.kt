package com.example.app1

import android.Manifest
import android.content.pm.PackageManager
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.media.MediaPlayer
import android.os.Bundle
import android.util.Base64
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.SystemBarStyle
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import kotlinx.coroutines.*
import okhttp3.*
import java.io.File
import java.io.FileOutputStream
import java.io.IOException
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.sp

class MainActivity : ComponentActivity() {
    private val WEBSOCKET_URL = "ws://10.203.240.23:8765"
    private var audioRecord: AudioRecord? = null
    private var isRecording by mutableStateOf(false)
    private var connectionStatus by mutableStateOf("Connecting to server")
    private var isConnected by mutableStateOf(false)
    private var secondsElapsed by mutableStateOf(0)
    private var webSocket: WebSocket? = null
    private val client = OkHttpClient()

    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted: Boolean ->
        if (isGranted) {
            startAudioStreaming()
        } else {
            connectionStatus = "Microphone permission denied"
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        enableEdgeToEdge(
            statusBarStyle = SystemBarStyle.dark(android.graphics.Color.TRANSPARENT),
            navigationBarStyle = SystemBarStyle.dark(android.graphics.Color.TRANSPARENT)
        )

        setContent {
            MyApp()
        }
    }


    private fun playAudioFromBase64(base64Audio: String) {
        try {
            val audioBytes = Base64.decode(base64Audio, Base64.DEFAULT)

            stopAudioStreaming()

            // Save to a temporary MP3 file
            val tempFile = File.createTempFile("tts_audio", ".mp3", cacheDir)
            FileOutputStream(tempFile).use { it.write(audioBytes) }

            val mediaPlayer = MediaPlayer()
            mediaPlayer.setDataSource(tempFile.absolutePath)
            mediaPlayer.prepare()
            mediaPlayer.setOnCompletionListener {
                it.release()
                tempFile.delete() // cleanup after playback
                // Resume recording after playback
                checkPermissionAndStart()
            }
            mediaPlayer.start()
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    // ------------------------
    // WEBSOCKET
    // ------------------------
    private fun setupWebSocket() {
        val request = Request.Builder().url(WEBSOCKET_URL).build()
        webSocket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                runOnUiThread {
                    connectionStatus = "Connected"
                    isConnected = true
                    startRecordingTimer()
                    checkPermissionAndStart()
                }
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                if (text.startsWith("AUDIO:")) {
                    val base64Audio = text.removePrefix("AUDIO:")
                    runOnUiThread {
                        playAudioFromBase64(base64Audio)
                    }
                }
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                runOnUiThread {
                    connectionStatus = "Connection Failed: ${t.message}"
                    isConnected = false
                }
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                runOnUiThread {
                    connectionStatus = "Connection Closed"
                    isConnected = false
                }
            }
        })
    }

    private fun startRecordingTimer() {
        CoroutineScope(Dispatchers.Main).launch {
            while (isConnected) {
                delay(1000)
                secondsElapsed++
            }
        }
    }

    private fun checkPermissionAndStart() {
        when {
            ContextCompat.checkSelfPermission(
                this,
                Manifest.permission.RECORD_AUDIO
            ) == PackageManager.PERMISSION_GRANTED -> {
                startAudioStreaming()
            }
            else -> {
                requestPermissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
            }
        }
    }

    private fun startAudioStreaming() {
        val sampleRate = 16000
        val bufferSize = AudioRecord.getMinBufferSize(
            sampleRate,
            AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT
        )

        audioRecord = AudioRecord(
            MediaRecorder.AudioSource.MIC,
            sampleRate,
            AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT,
            bufferSize
        )

        audioRecord?.startRecording()
        isRecording = true

        CoroutineScope(Dispatchers.IO).launch {
            val buffer = ByteArray(bufferSize)
            while (isRecording && isConnected) {
                val read = audioRecord?.read(buffer, 0, buffer.size) ?: 0
                if (read > 0) {
                    val base64Audio = Base64.encodeToString(buffer, 0, read, Base64.NO_WRAP)
                    try {
                        webSocket?.send("AUDIO:$base64Audio")
                    } catch (e: IOException) {
                        connectionStatus = "Audio send failed: ${e.message}"
                    }
                }
            }
        }
    }

    fun stopAudioStreaming() {
        isRecording = false
        try {
            audioRecord?.stop()
            audioRecord?.release()
        } catch (_: Exception) {
        }
        audioRecord = null
    }

    fun resetStreamingState() {
        stopAudioStreaming()
        webSocket?.close(1000, "Navigated away")
        isRecording = false
        isConnected = false
        secondsElapsed = 0
        connectionStatus = "Disconnected"
    }

    // ------------------------
    // UI
    // ------------------------
    @Composable
    fun MyApp() {
        val navController = rememberNavController()
        NavHost(navController, startDestination = "home") {
            composable("home") { AppUI(navController) }
            composable("second") { SecondScreen() }
        }
    }

    @Composable
    fun AppUI(navController: NavHostController) {
        Box(modifier = Modifier.fillMaxSize()) {
            // Background image
            Image(
                painter = painterResource(id = R.drawable.background),
                contentDescription = null,
                modifier = Modifier.fillMaxSize(),
                contentScale = ContentScale.Crop
            )

            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(24.dp),
                verticalArrangement = Arrangement.Center,
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Image(
                    painter = painterResource(id = R.drawable.logo),
                    contentDescription = "App Logo",
                    modifier = Modifier
                        .size(380.dp)
                        .padding(bottom = 2.dp)
                )

                Text(
                    text = "Hello Zapple",
                    fontSize = 28.sp,
                    fontWeight = FontWeight.Medium,
                    color = Color.White
                )

                Spacer(modifier = Modifier.height(16.dp))

                Text(
                    text = "Got anything to talk\nabout today?",
                    fontSize = 20.sp,
                    fontWeight = FontWeight.Normal,
                    color = Color.White,
                    textAlign = TextAlign.Center
                )

                Spacer(modifier = Modifier.height(48.dp))

                Button(
                    onClick = {
                        setupWebSocket()
                        navController.navigate("second")
                    },
                    shape = RoundedCornerShape(12.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = Color(0xFF333333),
                        contentColor = Color.White
                    ),
                    modifier = Modifier
                        .width(180.dp)
                        .height(52.dp)
                ) {
                    Text("Launch", fontSize = 18.sp, fontWeight = FontWeight.SemiBold)
                }
            }
        }
    }

    @Composable
    fun SecondScreen() {
        val context = LocalContext.current as MainActivity

        DisposableEffect(Unit) {
            onDispose {
                context.resetStreamingState()
            }
        }

        Box(
            modifier = Modifier.fillMaxSize(),
            contentAlignment = Alignment.Center
        ) {
            Image(
                painter = painterResource(id = R.drawable.background),
                contentDescription = null,
                modifier = Modifier.fillMaxSize(),
                contentScale = ContentScale.Crop
            )

            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center,
                modifier = Modifier.padding(24.dp)
            ) {
                Text(
                    text = connectionStatus,
                    fontSize = 24.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color.White
                )

                if (isConnected) {
                    Spacer(modifier = Modifier.height(16.dp))
                    Text(
                        text = "$secondsElapsed s",
                        fontSize = 20.sp,
                        color = Color.White
                    )
                    Spacer(modifier = Modifier.height(16.dp))
                    Text(
                        text = if (isRecording) "Streaming audio..." else "Ready",
                        color = Color.White,
                        fontSize = 16.sp
                    )
                } else {
                    Spacer(modifier = Modifier.height(16.dp))
                    Button(
                        onClick = { setupWebSocket() },
                        colors = ButtonDefaults.buttonColors(
                            containerColor = Color.Blue,
                            contentColor = Color.White
                        )
                    ) {
                        Text("Reconnect")
                    }
                }
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        resetStreamingState()
        client.dispatcher.executorService.shutdown()
    }
}
